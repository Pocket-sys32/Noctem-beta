"""Lead scoring algorithm — ranks loads against a carrier's profile."""

from __future__ import annotations

import math
from app.models.schemas import CarrierProfileOut, LoadOut, ScoredLoad


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    rlat1, rlng1, rlat2, rlng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _lane_score(carrier: CarrierProfileOut, load: LoadOut) -> float:
    """0-1 score: how well does the load match a preferred lane."""
    if not carrier.preferred_lanes:
        return 0.5  # neutral if no preferences set

    best = 0.0
    load_origin = f"{load.origin_city}, {load.origin_state}".lower()
    load_dest = f"{load.dest_city}, {load.dest_state}".lower()

    for lane in carrier.preferred_lanes:
        origin_match = 1.0 if lane.origin.lower() in load_origin or load_origin in lane.origin.lower() else 0.0
        dest_match = 1.0 if lane.destination.lower() in load_dest or load_dest in lane.destination.lower() else 0.0
        score = (origin_match + dest_match) / 2.0
        best = max(best, score)
    return best


def _equipment_score(carrier: CarrierProfileOut, load: LoadOut) -> float:
    if not carrier.equipment_types:
        return 0.5
    return 1.0 if load.equipment_type in carrier.equipment_types else 0.0


def _rate_score(load: LoadOut) -> float:
    """Normalize rate_per_mile into 0-1 (assumes $1-$5 range)."""
    if not load.rate_per_mile:
        return 0.5
    return min(max((load.rate_per_mile - 1.0) / 4.0, 0.0), 1.0)


def score_load(
    carrier: CarrierProfileOut,
    load: LoadOut,
    market_trend_bonus: float = 0.0,
) -> ScoredLoad:
    lane = _lane_score(carrier, load)
    equip = _equipment_score(carrier, load)
    rate = _rate_score(load)
    trend = min(max(market_trend_bonus, 0.0), 1.0)

    fit = round(
        (0.30 * lane + 0.25 * equip + 0.25 * rate + 0.20 * trend) * 100, 1
    )

    breakdown = {
        "lane_match": round(lane * 100, 1),
        "equipment_match": round(equip * 100, 1),
        "rate_score": round(rate * 100, 1),
        "market_trend": round(trend * 100, 1),
    }

    return ScoredLoad(
        **load.model_dump(),
        fit_score=fit,
        score_breakdown=breakdown,
    )
