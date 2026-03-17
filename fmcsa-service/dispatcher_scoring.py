from __future__ import annotations

from dispatcher_models import (
    BestFitScore,
    CarrierProfile,
    LoadOpportunity,
    MarketMetricsInterval,
    NegotiationInsight,
)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def compute_market_hotness(
    load_truck_ratio: float, rate_momentum: float, volatility_inverse: float
) -> float:
    """
    MHI = w1*norm(load_truck_ratio) + w2*norm(rate_momentum) + w3*norm(volatility_inverse)
    Weighting tuned for explainability-first MVP.
    """
    n_ratio = _clamp(load_truck_ratio / 8.0, 0, 1)
    n_momentum = _clamp((rate_momentum + 0.5) / 1.0, 0, 1)
    n_volatility_inv = _clamp(volatility_inverse, 0, 1)
    score = 100.0 * ((0.5 * n_ratio) + (0.3 * n_momentum) + (0.2 * n_volatility_inv))
    return round(_clamp(score, 0, 100), 2)


def score_load_for_carrier(
    profile: CarrierProfile, load: LoadOpportunity, market: MarketMetricsInterval | None
) -> BestFitScore | None:
    if load.equipment_required not in profile.equipment_types:
        return None

    profile_fit = 100.0
    lane_pref = next(
        (
            lane
            for lane in profile.preferred_lanes
            if lane.origin_region == load.origin_region_id and lane.destination_region == load.destination_region_id
        ),
        None,
    )
    lane_fit = 65.0
    if lane_pref:
        lane_fit = _clamp(60 + (lane_pref.weight * 8), 0, 100)

    market_timing = market.hotness_index if market else 50.0
    revenue_per_mile = load.offered_rate / load.distance_miles
    margin_gap = revenue_per_mile - profile.rate_floor_per_mile
    profitability = _clamp(50 + (margin_gap * 40), 0, 100)

    total = (0.35 * profile_fit) + (0.25 * lane_fit) + (0.2 * market_timing) + (0.2 * profitability)
    total = round(_clamp(total, 0, 100), 2)

    explanation = {
        "equipment_match": True,
        "lane_preference_hit": bool(lane_pref),
        "revenue_per_mile": round(revenue_per_mile, 2),
        "rate_floor_per_mile": profile.rate_floor_per_mile,
        "market_hotness_index": market_timing,
        "weights": {
            "profile_fit": 0.35,
            "lane_fit": 0.25,
            "market_timing": 0.2,
            "profitability": 0.2,
        },
    }
    return BestFitScore(
        load_id=load.load_id,
        carrier_id=profile.carrier_id,
        score_total=total,
        score_profile_fit=round(profile_fit, 2),
        score_lane_fit=round(lane_fit, 2),
        score_market_timing=round(market_timing, 2),
        score_profitability=round(profitability, 2),
        explanation_json=explanation,
    )


def build_negotiation_insight(
    profile: CarrierProfile, load: LoadOpportunity, market: MarketMetricsInterval | None
) -> NegotiationInsight:
    revenue_per_mile = load.offered_rate / load.distance_miles
    floor = profile.rate_floor_per_mile
    hotness = market.hotness_index if market else 50.0

    # Tight market allows stronger counter.
    uplift_multiplier = 1.02 + ((hotness / 100) * 0.08)
    floor_total = floor * load.distance_miles
    base_counter = max(load.offered_rate * uplift_multiplier, floor_total * (1 + profile.target_margin_pct / 100.0))

    confidence = _clamp(0.55 + (hotness / 250), 0.5, 0.95)
    delta = round(base_counter - load.offered_rate, 2)
    summary = (
        f"Market hotness in {load.origin_region_id} is {round(hotness, 1)}. "
        f"Suggest countering at ${round(base_counter, 2)} (about ${delta} above offer) "
        "to protect margin while leveraging current demand."
    )

    evidence = {
        "offered_rate": load.offered_rate,
        "counter_rate": round(base_counter, 2),
        "distance_miles": load.distance_miles,
        "offered_rate_per_mile": round(revenue_per_mile, 2),
        "carrier_rate_floor_per_mile": floor,
        "target_margin_pct": profile.target_margin_pct,
        "market_hotness_index": round(hotness, 2),
    }
    return NegotiationInsight(
        load_id=load.load_id,
        carrier_id=profile.carrier_id,
        recommended_counter_rate=round(base_counter, 2),
        confidence=round(confidence, 2),
        rationale_summary=summary,
        market_evidence_json=evidence,
    )
