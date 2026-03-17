"""Voice PIN linking routes.

Flow:
- Authenticated dashboard user requests a short-lived PIN.
- Caller says the PIN to the voice agent.
- Voice agent calls /voice/tool-call -> link_with_pin to bind the call to a carrier_id.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.db import get_supabase

router = APIRouter(prefix="/pins", tags=["pins"])


def _generate_pin() -> str:
    return f"{random.randint(0, 999999):06d}"


@router.post("/voice", response_model=dict)
async def create_voice_pin(user_id: str = Depends(get_user_id)):
    """Create a 6-digit PIN that expires in 10 minutes."""
    sb = get_supabase()
    profile_resp = sb.table("carrier_profiles").select("id").eq("user_id", user_id).execute()
    if not profile_resp.data:
        raise HTTPException(status_code=404, detail="No carrier profile found. Complete onboarding first.")

    carrier_id = profile_resp.data[0]["id"]
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Try a few times to avoid collisions
    for _ in range(6):
        pin = _generate_pin()
        existing = (
            sb.table("voice_pins")
            .select("id")
            .eq("pin", pin)
            .is_("used_at", "null")
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .execute()
        )
        if not existing.data:
            insert = {
                "carrier_id": carrier_id,
                "pin": pin,
                "expires_at": expires_at.isoformat(),
            }
            created = sb.table("voice_pins").insert(insert).execute()
            if not created.data:
                raise HTTPException(status_code=500, detail="Failed to create PIN")
            return {"pin": pin, "expires_at": expires_at.isoformat(), "carrier_id": carrier_id}

    raise HTTPException(status_code=500, detail="Failed to generate unique PIN. Try again.")


@router.post("/voice/resolve", response_model=dict)
async def resolve_voice_pin(body: dict):
    """Resolve a PIN to carrier_id and mark it used. Called by the voice tool handler."""
    pin_raw = str(body.get("pin", "")).strip()
    if not pin_raw.isdigit() or len(pin_raw) != 6:
        raise HTTPException(status_code=400, detail="PIN must be a 6-digit number")

    now = datetime.now(timezone.utc).isoformat()
    sb = get_supabase()

    resp = (
        sb.table("voice_pins")
        .select("*")
        .eq("pin", pin_raw)
        .is_("used_at", "null")
        .gt("expires_at", now)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="PIN not found or expired")

    row = resp.data[0]
    sb.table("voice_pins").update({"used_at": now}).eq("id", row["id"]).execute()
    return {"carrier_id": row["carrier_id"]}

