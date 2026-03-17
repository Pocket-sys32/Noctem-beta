"""Seed script — populates the loads and market_indices tables with realistic mock data.

Usage:
    cd backend
    uv run python -m seed.seed_data
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Reference data ────────────────────────────────────────────

CITIES = [
    ("Los Angeles", "CA", 34.0522, -118.2437),
    ("Chicago", "IL", 41.8781, -87.6298),
    ("Dallas", "TX", 32.7767, -96.7970),
    ("Atlanta", "GA", 33.7490, -84.3880),
    ("Fresno", "CA", 36.7378, -119.7871),
    ("Memphis", "TN", 35.1495, -90.0490),
    ("Indianapolis", "IN", 39.7684, -86.1581),
    ("Columbus", "OH", 39.9612, -82.9988),
    ("Jacksonville", "FL", 30.3322, -81.6557),
    ("Laredo", "TX", 27.5036, -99.5076),
    ("Manteca", "CA", 37.7975, -121.2161),
    ("Phoenix", "AZ", 33.4484, -112.0740),
    ("Denver", "CO", 39.7392, -104.9903),
    ("Kansas City", "MO", 39.0997, -94.5786),
    ("Nashville", "TN", 36.1627, -86.7816),
    ("Houston", "TX", 29.7604, -95.3698),
    ("Seattle", "WA", 47.6062, -122.3321),
    ("Portland", "OR", 45.5152, -122.6784),
    ("Miami", "FL", 25.7617, -80.1918),
    ("Charlotte", "NC", 35.2271, -80.8431),
    ("Detroit", "MI", 42.3314, -83.0458),
    ("Salt Lake City", "UT", 40.7608, -111.8910),
    ("El Paso", "TX", 31.7619, -106.4850),
    ("Albuquerque", "NM", 35.0844, -106.6504),
    ("Reno", "NV", 39.5296, -119.8138),
]

EQUIPMENT_TYPES = ["dry_van", "reefer", "flatbed", "step_deck", "tanker"]
EQUIPMENT_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]

BROKERS = [
    ("TQL Freight", "MC-248710"),
    ("CH Robinson", "MC-236346"),
    ("Echo Global", "MC-416124"),
    ("XPO Logistics", "MC-195011"),
    ("Landstar", "MC-143546"),
    ("Coyote Logistics", "MC-568329"),
    ("JB Hunt", "MC-156287"),
    ("Schneider", "MC-133655"),
    ("Werner", "MC-141092"),
    ("BNSF Logistics", "MC-309573"),
]


def _random_rate(equip: str, miles: int) -> float:
    base = {"dry_van": 2.10, "reefer": 2.60, "flatbed": 2.80, "step_deck": 3.00, "tanker": 3.20}
    r = base.get(equip, 2.20) + random.uniform(-0.40, 0.60)
    if miles < 300:
        r += 0.30
    return round(r, 2)


def _haversine_miles(lat1, lng1, lat2, lng2):
    import math
    R = 3958.8
    rlat1, rlng1, rlat2, rlng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return int(R * 2 * math.asin(math.sqrt(a)))


def generate_loads(n: int = 65) -> list[dict]:
    loads = []
    today = date.today()
    for _ in range(n):
        origin = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c[0] != origin[0]])
        equip = random.choices(EQUIPMENT_TYPES, weights=EQUIPMENT_WEIGHTS, k=1)[0]
        miles = _haversine_miles(origin[2], origin[3], dest[2], dest[3])
        rpm = _random_rate(equip, miles)
        broker = random.choice(BROKERS)
        pickup = today + timedelta(days=random.randint(1, 14))

        loads.append({
            "origin_city": origin[0],
            "origin_state": origin[1],
            "origin_lat": origin[2],
            "origin_lng": origin[3],
            "dest_city": dest[0],
            "dest_state": dest[1],
            "dest_lat": dest[2],
            "dest_lng": dest[3],
            "equipment_type": equip,
            "weight_lbs": random.randint(10000, 45000),
            "rate_per_mile": rpm,
            "total_rate": round(rpm * miles, 2),
            "miles": miles,
            "pickup_date": pickup.isoformat(),
            "delivery_date": (pickup + timedelta(days=max(1, miles // 500))).isoformat(),
            "broker_name": broker[0],
            "broker_mc": broker[1],
            "status": "available",
        })
    return loads


MARKET_REGIONS = [
    ("Los Angeles, CA", 34.0522, -118.2437),
    ("Chicago, IL", 41.8781, -87.6298),
    ("Dallas, TX", 32.7767, -96.7970),
    ("Atlanta, GA", 33.7490, -84.3880),
    ("Fresno, CA", 36.7378, -119.7871),
    ("Memphis, TN", 35.1495, -90.0490),
    ("Indianapolis, IN", 39.7684, -86.1581),
    ("Columbus, OH", 39.9612, -82.9988),
    ("Jacksonville, FL", 30.3322, -81.6557),
    ("Laredo, TX", 27.5036, -99.5076),
    ("Manteca, CA", 37.7975, -121.2161),
    ("Phoenix, AZ", 33.4484, -112.0740),
    ("Denver, CO", 39.7392, -104.9903),
    ("Kansas City, MO", 39.0997, -94.5786),
    ("Nashville, TN", 36.1627, -86.7816),
]


def generate_market_indices() -> list[dict]:
    indices = []
    for region, lat, lng in MARKET_REGIONS:
        ratio = round(random.uniform(0.5, 3.0), 2)
        avg_rpm = round(random.uniform(1.80, 3.50), 2)
        if ratio > 1.5:
            trend = "up"
        elif ratio < 0.8:
            trend = "down"
        else:
            trend = "stable"
        equip = random.choice(EQUIPMENT_TYPES[:3])

        indices.append({
            "region": region,
            "lat": lat,
            "lng": lng,
            "load_to_truck_ratio": ratio,
            "avg_rate_per_mile": avg_rpm,
            "trend": trend,
            "equipment_type": equip,
        })
    return indices


def main():
    print("Clearing existing seed data...")
    sb.table("loads").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("market_indices").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    loads = generate_loads(65)
    print(f"Inserting {len(loads)} loads...")
    sb.table("loads").insert(loads).execute()

    indices = generate_market_indices()
    print(f"Inserting {len(indices)} market indices...")
    sb.table("market_indices").insert(indices).execute()

    print("Seed complete.")


if __name__ == "__main__":
    main()
