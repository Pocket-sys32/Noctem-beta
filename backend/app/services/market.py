"""Market hotness computation — derives indices from load data."""

from __future__ import annotations

from app.db import get_supabase
from app.models.schemas import MarketIndexOut

# Simulated average truck counts per region for MVP
_SIMULATED_TRUCKS: dict[str, int] = {
    "Los Angeles, CA": 320,
    "Chicago, IL": 280,
    "Dallas, TX": 260,
    "Atlanta, GA": 220,
    "Fresno, CA": 90,
    "Memphis, TN": 150,
    "Indianapolis, IN": 130,
    "Columbus, OH": 120,
    "Jacksonville, FL": 100,
    "Laredo, TX": 75,
    "Manteca, CA": 40,
    "Phoenix, AZ": 180,
    "Denver, CO": 140,
    "Kansas City, MO": 110,
    "Nashville, TN": 100,
}


async def compute_market_indices() -> list[MarketIndexOut]:
    """Recompute market indices from current load data and store them."""
    sb = get_supabase()

    loads_resp = sb.table("loads").select("*").eq("status", "available").execute()
    loads = loads_resp.data or []

    region_stats: dict[str, dict] = {}
    for load in loads:
        region = f"{load['origin_city']}, {load['origin_state']}"
        if region not in region_stats:
            region_stats[region] = {
                "count": 0,
                "total_rpm": 0.0,
                "lat": load.get("origin_lat"),
                "lng": load.get("origin_lng"),
                "equipment_counts": {},
            }
        region_stats[region]["count"] += 1
        rpm = load.get("rate_per_mile") or 0
        region_stats[region]["total_rpm"] += float(rpm)
        eq = load.get("equipment_type", "dry_van")
        region_stats[region]["equipment_counts"][eq] = region_stats[region]["equipment_counts"].get(eq, 0) + 1

    results = []
    for region, stats in region_stats.items():
        truck_count = _SIMULATED_TRUCKS.get(region, 80)
        ratio = round(stats["count"] / max(truck_count, 1), 2)
        avg_rpm = round(stats["total_rpm"] / max(stats["count"], 1), 2)

        if ratio > 1.5:
            trend = "up"
        elif ratio < 0.8:
            trend = "down"
        else:
            trend = "stable"

        top_equip = max(stats["equipment_counts"], key=stats["equipment_counts"].get) if stats["equipment_counts"] else "dry_van"

        row = {
            "region": region,
            "lat": stats["lat"],
            "lng": stats["lng"],
            "load_to_truck_ratio": ratio,
            "avg_rate_per_mile": avg_rpm,
            "trend": trend,
            "equipment_type": top_equip,
        }

        results.append(MarketIndexOut(id="pending", computed_at=None, **row))

    # Upsert into DB (clear old, insert new)
    sb.table("market_indices").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    if results:
        rows = [{k: v for k, v in r.model_dump().items() if k not in ("id", "computed_at")} for r in results]
        sb.table("market_indices").insert(rows).execute()

    fresh = sb.table("market_indices").select("*").execute()
    return [MarketIndexOut(**r) for r in (fresh.data or [])]


async def get_market_indices() -> list[MarketIndexOut]:
    sb = get_supabase()
    resp = sb.table("market_indices").select("*").order("load_to_truck_ratio", desc=True).execute()
    return [MarketIndexOut(**r) for r in (resp.data or [])]


def get_trend_bonus(origin_city: str, origin_state: str, indices: list[MarketIndexOut]) -> float:
    """Return a 0-1 bonus for a load's origin region based on market trend."""
    region = f"{origin_city}, {origin_state}"
    for idx in indices:
        if idx.region.lower() == region.lower():
            if idx.trend == "up":
                return 0.9
            elif idx.trend == "stable":
                return 0.5
            else:
                return 0.2
    return 0.5
