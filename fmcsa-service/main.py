import json
import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from dispatcher_models import (
    ActionAudit,
    CarrierAuthorityStatus,
    CarrierProfile,
    CarrierProfilePatch,
    EquipmentType,
    LanePreference,
    LoadOpportunity,
    MarketMetricsInterval,
)
from dispatcher_scoring import build_negotiation_insight, compute_market_hotness, score_load_for_carrier
from dispatcher_store import DispatcherStore
from dispatcher_voice import confirmation_prompt, parse_intent
from fmcsa import FMCSAClient

load_dotenv()

MC_PREFIX = re.compile(r"^mc[-\s]*", re.IGNORECASE)

# Fails fast at startup if FMCSA_WEB_KEY is not set
client = FMCSAClient()
store = DispatcherStore()


class GoogleLoginRequest(BaseModel):
    email: str
    name: str


class OnboardingRequest(BaseModel):
    mc_number: str
    company_name_override: str | None = None


class MarketMetricsUpsertRequest(BaseModel):
    region_id: str
    load_count: int = Field(ge=0)
    truck_count: int = Field(ge=0)
    avg_rate_per_mile: float = Field(ge=0)
    rate_momentum: float = 0.0
    rate_volatility_idx: float = Field(ge=0)
    window_hours: int = Field(default=4, ge=1, le=24)


class VoiceQueryRequest(BaseModel):
    carrier_id: UUID
    caller_number: str
    utterance: str
    confirmation: bool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()


app = FastAPI(title="Noctem FMCSA Service", lifespan=lifespan)


def _normalize_mc(value: str) -> str:
    return MC_PREFIX.sub("", value.strip())


@app.get("/carriers/{mc_number}")
async def get_carrier(mc_number: str):
    normalized = _normalize_mc(mc_number)
    if not normalized.isdigit():
        raise HTTPException(status_code=400, detail="MC number must be numeric")

    try:
        carrier = await client.lookup_mc(normalized)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"FMCSA API error: {e.response.status_code}")

    if carrier is None:
        raise HTTPException(status_code=404, detail=f"No carrier found for MC {normalized}")

    return carrier


@app.post("/auth/google/mock")
async def google_login(payload: GoogleLoginRequest):
    # OAuth token validation is provider-specific; this endpoint is a local contract stub.
    return {
        "user": {"email": payload.email, "name": payload.name},
        "session": {"access_token": f"mock-{payload.email}", "provider": "google"},
    }


@app.post("/onboarding/mc")
async def onboarding_from_mc(payload: OnboardingRequest):
    normalized = _normalize_mc(payload.mc_number)
    if not normalized.isdigit():
        raise HTTPException(status_code=400, detail="MC number must be numeric")

    carrier = await client.lookup_mc(normalized)
    if not carrier:
        raise HTTPException(status_code=404, detail=f"No carrier found for MC {normalized}")

    authority = CarrierAuthorityStatus.active if carrier.allowed_to_operate else CarrierAuthorityStatus.inactive
    profile = CarrierProfile(
        mc_number=normalized,
        company_name=payload.company_name_override or carrier.legal_name or carrier.dba_name or "Unknown carrier",
        dot_number=carrier.dot_number,
        authority_status=authority,
        equipment_types=[EquipmentType.dry_van],
        operating_regions=[carrier.state or "unknown"],
        preferred_lanes=[LanePreference(origin_region=carrier.state or "unknown", destination_region="chicago", weight=1.0)],
    )
    saved = store.upsert_profile(profile, event_type="CarrierProfileCreated")
    return {"carrier_profile": saved, "message": "Carrier profile initialized from MC number."}


@app.get("/carrier-profile/{carrier_id}")
async def get_carrier_profile(carrier_id: UUID):
    profile = store.get_profile(carrier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")
    return profile


@app.patch("/carrier-profile/{carrier_id}")
async def patch_carrier_profile(carrier_id: UUID, patch: CarrierProfilePatch):
    profile = store.patch_profile(carrier_id, patch)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")
    return profile


@app.get("/carrier-profile/{carrier_id}/sync-status")
async def carrier_profile_sync_status(carrier_id: UUID):
    profile = store.get_profile(carrier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")
    last_cache = store.cache_updated_at.get(carrier_id)
    stale_seconds = (datetime.now(UTC) - last_cache).total_seconds() if last_cache else None
    return {
        "carrier_id": carrier_id,
        "profile_version": profile.profile_version,
        "last_cache_refresh_at": last_cache,
        "stale_seconds": stale_seconds,
        "within_target_5s": stale_seconds is not None and stale_seconds <= 5.0,
    }


@app.post("/market/metrics")
async def upsert_market_metrics(payload: MarketMetricsUpsertRequest):
    end = datetime.now(UTC)
    start = end - timedelta(hours=payload.window_hours)
    ratio = payload.load_count / payload.truck_count if payload.truck_count else float(payload.load_count)
    volatility_inverse = 1.0 / (1.0 + payload.rate_volatility_idx)
    hotness = compute_market_hotness(ratio, payload.rate_momentum, volatility_inverse)

    metrics = MarketMetricsInterval(
        region_id=payload.region_id,
        interval_start=start,
        interval_end=end,
        load_count=payload.load_count,
        truck_count=payload.truck_count,
        load_truck_ratio=round(ratio, 2),
        avg_rate_per_mile=payload.avg_rate_per_mile,
        rate_momentum=payload.rate_momentum,
        rate_volatility_idx=payload.rate_volatility_idx,
        hotness_index=hotness,
    )
    return store.upsert_market_metrics(metrics)


@app.get("/market/overview")
async def market_overview():
    return {"regions": list(store.market_metrics.values())}


@app.post("/loads")
async def add_load(load: LoadOpportunity):
    return store.add_load(load)


@app.get("/loads/recommended/{carrier_id}")
async def recommended_loads(carrier_id: UUID):
    profile = store.get_profile(carrier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")

    ranked: list[tuple] = []
    for load in store.loads.values():
        market = store.market_metrics.get(load.origin_region_id)
        score = score_load_for_carrier(profile, load, market)
        if not score:
            continue
        insight = build_negotiation_insight(profile, load, market)
        store.add_score(score)
        store.add_negotiation(insight)
        ranked.append((score.score_total, load, score, insight))

    ranked.sort(key=lambda row: row[0], reverse=True)
    response = []
    for _, load, score, insight in ranked[:10]:
        response.append(
            {
                "load": load,
                "best_fit_score": score,
                "negotiation_insight": insight,
                "profitability_badge": "high"
                if score.score_profitability >= 75
                else "medium"
                if score.score_profitability >= 50
                else "low",
            }
        )
    return {"recommendations": response}


@app.post("/voice/query")
async def voice_query(payload: VoiceQueryRequest):
    profile = store.get_profile(payload.carrier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")

    session = next(
        (s for s in store.sessions.values() if s.carrier_id == payload.carrier_id and s.caller_number == payload.caller_number),
        None,
    )
    parsed = parse_intent(payload.utterance)
    if session is None:
        from dispatcher_models import CallSession, TranscriptTurn

        session = CallSession(
            carrier_id=payload.carrier_id,
            caller_number=payload.caller_number,
            language_detected=parsed.language,
        )
        store.add_session(session)

    from dispatcher_models import TranscriptTurn

    turn_index = len([t for t in store.transcripts if t.session_id == session.session_id]) + 1
    store.add_transcript_turn(
        TranscriptTurn(
            session_id=session.session_id,
            turn_index=turn_index,
            speaker="driver",
            text=payload.utterance,
            language=parsed.language,
            intent=parsed.intent,
            entities_json=parsed.entities,
        )
    )

    if parsed.intent == "get_best_load":
        recs = await recommended_loads(payload.carrier_id)
        top = recs["recommendations"][0] if recs["recommendations"] else None
        if not top:
            text = "I don't see a matching load right now. I can keep monitoring and alert you."
        else:
            load = top["load"]
            insight = top["negotiation_insight"]
            text = (
                f"Your best load is from {load.origin_region_id} to {load.destination_region_id}. "
                f"Offered rate is ${load.offered_rate}. {insight.rationale_summary}"
            )
    elif parsed.intent == "update_preferred_lane":
        destination = parsed.entities.get("destination_region", "unknown")
        if parsed.requires_confirmation and payload.confirmation is not True:
            text = confirmation_prompt(parsed.language, destination)
        else:
            updated_lanes = list(profile.preferred_lanes)
            updated_lanes.append(
                LanePreference(
                    origin_region=parsed.entities.get("origin_region", "current_region"),
                    destination_region=destination,
                    weight=1.1,
                )
            )
            store.patch_profile(profile.carrier_id, CarrierProfilePatch(preferred_lanes=updated_lanes))
            text = f"Done. Your preferred lane now includes destination {destination}."
    else:
        text = "I can help with best-load search and lane preference updates. Ask me for your best load near you."

    store.add_audit(
        ActionAudit(
            session_id=session.session_id,
            actor_type="voice",
            action_name=parsed.intent,
            request_json=payload.model_dump(mode="json"),
            result_json={"response": text},
        )
    )

    store.add_transcript_turn(
        TranscriptTurn(
            session_id=session.session_id,
            turn_index=turn_index + 1,
            speaker="agent",
            text=text,
            language=parsed.language,
            intent=parsed.intent,
            entities_json=parsed.entities,
        )
    )
    return {
        "session_id": session.session_id,
        "language_detected": parsed.language,
        "intent": parsed.intent,
        "response": text,
    }


@app.get("/voice/status/{carrier_id}")
async def voice_status(carrier_id: UUID):
    profile = store.get_profile(carrier_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Carrier profile not found")
    return {
        "carrier_id": carrier_id,
        "recent_transcripts": store.latest_transcripts(carrier_id, limit=25),
        "recent_actions": [a for a in store.audit_log if a.actor_type == "voice"][-25:],
    }


@app.get("/delivery/phases")
async def delivery_phases():
    return {
        "phase_1_mvp": [
            "Google OAuth contract stub and MC onboarding",
            "CarrierProfile source-of-truth + profile events",
            "Mock market metrics ingest + market hotness scoring",
            "Best-fit ranking + negotiation insight generation",
            "Multilingual voice query endpoint (en/pa/es) with confirmation safeguards",
            "Voice transcript and action audit panel data endpoints",
        ],
        "phase_2_integrations": [
            "External loadboard adapters (DAT/Truckstop) with normalization",
            "Negotiation model calibration from acceptance outcomes",
            "Dialect-focused NLU tuning for Punjabi and Spanish regional variants",
            "SLA hardening with retry policies and circuit breakers",
        ],
        "targets": {
            "voice_p95_response_seconds": 2.5,
            "profile_propagation_seconds": 5,
            "market_refresh_minutes": "1-5",
        },
    }


@app.post("/tool-call")
async def vapi_tool_call(request: Request):
    """Vapi server-side tool call endpoint."""
    body = await request.json()
    tool_calls = body.get("message", {}).get("toolCallList", [])

    results = []
    for call in tool_calls:
        call_id = call.get("id")
        name = call.get("function", {}).get("name")
        args = json.loads(call.get("function", {}).get("arguments", "{}"))

        if name == "lookup_mc":
            result = await _handle_lookup_mc(args)
        elif name == "get_best_load":
            result = await _handle_best_load(args)
        else:
            result = f"Unknown tool: {name}"

        results.append({"toolCallId": call_id, "result": result})

    return {"results": results}


async def _handle_lookup_mc(args: dict) -> str:
    mc_raw = args.get("mc_number", "")
    normalized = _normalize_mc(str(mc_raw))
    if not normalized.isdigit():
        return "I couldn't understand that MC number. Could you repeat it?"

    try:
        carrier = await client.lookup_mc(normalized)
    except httpx.HTTPStatusError:
        return "I'm having trouble reaching the carrier database right now. Please try again in a moment."

    if carrier is None:
        return f"I couldn't find any carrier registered under MC {normalized}."

    name = carrier.legal_name or carrier.dba_name or "Unknown carrier"
    status = "authorized to operate" if carrier.allowed_to_operate else "NOT authorized to operate"
    oos = " They are currently out of service." if carrier.out_of_service else ""
    location = f" Based in {carrier.city}, {carrier.state}." if carrier.city and carrier.state else ""

    return f"{name} is {status}.{oos}{location} Their DOT number is {carrier.dot_number}."


async def _handle_best_load(args: dict) -> str:
    carrier_id_raw = args.get("carrier_id")
    if not carrier_id_raw:
        return "Please provide carrier_id so I can fetch recommended loads."
    try:
        carrier_id = UUID(str(carrier_id_raw))
    except ValueError:
        return "carrier_id must be a valid UUID."

    recs = await recommended_loads(carrier_id)
    top = recs["recommendations"][0] if recs["recommendations"] else None
    if not top:
        return "No matching loads are available right now for this carrier profile."
    load = top["load"]
    score = top["best_fit_score"]
    return (
        f"Top load is {load.origin_region_id} to {load.destination_region_id} "
        f"with best-fit score {score.score_total} and offered rate ${load.offered_rate}."
    )
