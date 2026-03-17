"""Voice tool-call handler — receives tool calls from the OpenAI Realtime voice agent."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request

from app.db import get_supabase
from app.models.schemas import CarrierProfileOut, LoadOut
from app.services.matching import score_load
from app.services.market import get_market_indices, get_trend_bonus

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/tool-call")
async def handle_tool_call(request: Request):
    """Unified tool-call endpoint for the voice agent.

    Expects JSON body with: { "tool": "<name>", "args": {...}, "carrier_id": "..." }
    """
    body = await request.json()
    tool = body.get("tool", "")
    args = body.get("args", {})
    carrier_id = body.get("carrier_id")

    handlers = {
        "lookup_carrier": _handle_lookup_carrier,
        "get_recommended_loads": _handle_recommended_loads,
        "update_preferred_lane": _handle_update_lane,
        "get_carrier_profile": _handle_get_profile,
        "link_with_pin": _handle_link_with_pin,
    }

    handler = handlers.get(tool)
    if not handler:
        return {"error": f"Unknown tool: {tool}"}

    result = await handler(args, carrier_id)
    return {"result": result}


async def _handle_lookup_carrier(args: dict, carrier_id: str | None) -> str:
    from app.services.fmcsa import FMCSAClient
    import re

    mc_raw = args.get("mc_number", "")
    mc = re.sub(r"^mc[-\s]*", "", str(mc_raw).strip(), flags=re.IGNORECASE)
    if not mc.isdigit():
        return "I couldn't understand that MC number. Could you repeat it?"

    fmcsa = FMCSAClient()
    try:
        carrier = await fmcsa.lookup_mc(mc)
    except Exception:
        return "I'm having trouble reaching the carrier database right now."
    finally:
        await fmcsa.aclose()

    if carrier is None:
        return f"I couldn't find any carrier registered under MC {mc}."

    name = carrier.legal_name or carrier.dba_name or "Unknown carrier"
    status = "authorized to operate" if carrier.allowed_to_operate else "NOT authorized to operate"
    oos = " They are currently out of service." if carrier.out_of_service else ""
    location = f" Based in {carrier.city}, {carrier.state}." if carrier.city and carrier.state else ""
    return f"{name} is {status}.{oos}{location} Their DOT number is {carrier.dot_number}."


async def _handle_recommended_loads(args: dict, carrier_id: str | None) -> str:
    if not carrier_id:
        return "I need your carrier profile to find loads. Please log in through the dashboard first."

    sb = get_supabase()
    profile_resp = sb.table("carrier_profiles").select("*").eq("id", carrier_id).execute()
    if not profile_resp.data:
        return "I couldn't find your carrier profile."

    carrier = CarrierProfileOut(**profile_resp.data[0])
    loads_resp = sb.table("loads").select("*").eq("status", "available").execute()
    loads = [LoadOut(**r) for r in (loads_resp.data or [])]
    indices = await get_market_indices()

    scored = []
    for load in loads:
        tb = get_trend_bonus(load.origin_city, load.origin_state, indices)
        scored.append(score_load(carrier, load, market_trend_bonus=tb))
    scored.sort(key=lambda s: s.fit_score, reverse=True)

    top3 = scored[:3]
    if not top3:
        return "I don't see any available loads matching your profile right now."

    lines = []
    for i, sl in enumerate(top3, 1):
        lines.append(
            f"{i}. {sl.origin_city}, {sl.origin_state} to {sl.dest_city}, {sl.dest_state} — "
            f"{sl.equipment_type.replace('_', ' ')}, {sl.miles} miles, ${sl.rate_per_mile}/mile, "
            f"{sl.fit_score}% match."
        )
    return "Here are your top loads:\n" + "\n".join(lines)


async def _handle_update_lane(args: dict, carrier_id: str | None) -> str:
    if not carrier_id:
        return "I need your carrier profile to update lanes."

    origin = args.get("origin", "")
    destination = args.get("destination", "")
    if not origin or not destination:
        return "I need both an origin and destination for the lane. Could you tell me both?"

    sb = get_supabase()
    profile_resp = sb.table("carrier_profiles").select("preferred_lanes").eq("id", carrier_id).execute()
    if not profile_resp.data:
        return "I couldn't find your carrier profile."

    lanes = profile_resp.data[0].get("preferred_lanes") or []
    lanes.append({"origin": origin, "destination": destination})
    sb.table("carrier_profiles").update({"preferred_lanes": lanes}).eq("id", carrier_id).execute()
    return f"Done! I've added {origin} to {destination} as a preferred lane."


async def _handle_get_profile(args: dict, carrier_id: str | None) -> str:
    if not carrier_id:
        return "I need your carrier profile information."

    sb = get_supabase()
    resp = sb.table("carrier_profiles").select("*").eq("id", carrier_id).execute()
    if not resp.data:
        return "I couldn't find your carrier profile."

    p = resp.data[0]
    name = p.get("legal_name") or p.get("dba_name") or "your company"
    equip = ", ".join(e.replace("_", " ") for e in (p.get("equipment_types") or [])) or "none set"
    lanes = p.get("preferred_lanes") or []
    lane_str = "; ".join(f"{l['origin']} to {l['destination']}" for l in lanes) if lanes else "none set"

    return (
        f"Your carrier is {name}, MC {p.get('mc_number')}. "
        f"Equipment: {equip}. Preferred lanes: {lane_str}. "
        f"Based in {p.get('home_city', '?')}, {p.get('home_state', '?')}."
    )


async def _handle_link_with_pin(args: dict, carrier_id: str | None) -> str:
    """Resolve a 6-digit PIN to a carrier_id for this call."""
    pin = str(args.get("pin", "")).strip()
    if not pin.isdigit() or len(pin) != 6:
        return "That PIN should be 6 digits. Please repeat it slowly."

    sb = get_supabase()
    # Use the same logic as /pins/voice/resolve but inline (service role)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    resp = (
        sb.table("voice_pins")
        .select("*")
        .eq("pin", pin)
        .is_("used_at", "null")
        .gt("expires_at", now)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return "I couldn't find that PIN, or it expired. Please generate a new one in the dashboard."

    row = resp.data[0]
    sb.table("voice_pins").update({"used_at": now}).eq("id", row["id"]).execute()
    cid = row["carrier_id"]
    return f"Linked. carrier_id:{cid}"
