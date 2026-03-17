"""Load search, matching, and recommendation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import get_user_id
from app.db import get_supabase
from app.models.schemas import CarrierProfileOut, LoadOut, ScoredLoad, MarketIndexOut
from app.services.matching import score_load
from app.services.market import get_market_indices, get_trend_bonus
from app.services.negotiation import generate_market_summary

router = APIRouter(prefix="/loads", tags=["loads"])


@router.get("/", response_model=list[LoadOut])
async def list_loads(
    status: str = Query("available"),
    equipment_type: str | None = None,
    origin_state: str | None = None,
    limit: int = Query(50, le=200),
):
    sb = get_supabase()
    q = sb.table("loads").select("*").eq("status", status).limit(limit)
    if equipment_type:
        q = q.eq("equipment_type", equipment_type)
    if origin_state:
        q = q.eq("origin_state", origin_state)
    resp = q.execute()
    return [LoadOut(**r) for r in (resp.data or [])]


@router.get("/recommended", response_model=list[ScoredLoad])
async def recommended_loads(
    user_id: str = Depends(get_user_id),
    limit: int = Query(20, le=50),
):
    """Score all available loads against the carrier's profile and return top matches."""
    sb = get_supabase()

    profile_resp = sb.table("carrier_profiles").select("*").eq("user_id", user_id).execute()
    if not profile_resp.data:
        return []
    carrier = CarrierProfileOut(**profile_resp.data[0])

    loads_resp = sb.table("loads").select("*").eq("status", "available").execute()
    loads = [LoadOut(**r) for r in (loads_resp.data or [])]

    indices = await get_market_indices()

    scored: list[ScoredLoad] = []
    for load in loads:
        trend_bonus = get_trend_bonus(load.origin_city, load.origin_state, indices)
        sl = score_load(carrier, load, market_trend_bonus=trend_bonus)
        scored.append(sl)

    scored.sort(key=lambda s: s.fit_score, reverse=True)
    top = scored[:limit]

    # Attach market summaries to top 5
    for sl in top[:5]:
        market = next(
            (m for m in indices if m.region.lower() == f"{sl.origin_city}, {sl.origin_state}".lower()),
            None,
        )
        sl.market_summary = await generate_market_summary(sl, market)

    return top
