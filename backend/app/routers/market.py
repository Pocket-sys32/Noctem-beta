"""Market analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import MarketIndexOut
from app.services.market import compute_market_indices, get_market_indices

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/", response_model=list[MarketIndexOut])
async def list_market_indices():
    return await get_market_indices()


@router.post("/refresh", response_model=list[MarketIndexOut])
async def refresh_market_indices():
    """Recompute market indices from current load data."""
    return await compute_market_indices()
