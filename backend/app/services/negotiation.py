"""GPT-powered negotiation intelligence — market analysis summaries per load."""

from __future__ import annotations

import os
from openai import AsyncOpenAI
from app.models.schemas import ScoredLoad, MarketIndexOut


_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _client


async def generate_market_summary(
    load: ScoredLoad,
    market: MarketIndexOut | None,
) -> str:
    """Generate a short negotiation-oriented market analysis for a load."""
    if not os.environ.get("OPENAI_API_KEY"):
        return _fallback_summary(load, market)

    client = _get_openai()

    market_ctx = ""
    if market:
        market_ctx = (
            f"The {market.region} market has a load-to-truck ratio of {market.load_to_truck_ratio} "
            f"and an average rate of ${market.avg_rate_per_mile}/mile. The trend is {market.trend}."
        )

    prompt = (
        f"You are a freight market analyst. Give a 2-sentence negotiation tip for a carrier.\n\n"
        f"Load: {load.origin_city}, {load.origin_state} → {load.dest_city}, {load.dest_state}\n"
        f"Equipment: {load.equipment_type}, {load.miles} miles, ${load.rate_per_mile}/mile offered\n"
        f"Fit score: {load.fit_score}%\n"
        f"{market_ctx}\n\n"
        f"Be specific with dollar amounts. Keep it under 50 words."
    )

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7,
    )
    return resp.choices[0].message.content or _fallback_summary(load, market)


def _fallback_summary(load: ScoredLoad, market: MarketIndexOut | None) -> str:
    """Deterministic fallback when OpenAI is unavailable."""
    if market and market.trend == "up":
        suggestion = f"Market is tight in {market.region}; consider requesting a ${0.25 + (market.load_to_truck_ratio or 1) * 0.1:.2f}/mile premium."
    elif market and market.trend == "down":
        suggestion = f"Market is soft in {market.region}; the offered rate of ${load.rate_per_mile}/mile is competitive."
    else:
        suggestion = f"Market is stable; ${load.rate_per_mile}/mile is in line with averages."
    return suggestion
