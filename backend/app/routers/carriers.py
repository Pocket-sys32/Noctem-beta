"""Carrier profile CRUD routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.db import get_supabase
from app.models.schemas import (
    CarrierProfileCreate,
    CarrierProfileOut,
    CarrierProfileUpdate,
)
from app.services.fmcsa import FMCSAClient

router = APIRouter(prefix="/carriers", tags=["carriers"])

MC_PREFIX = re.compile(r"^mc[-\s]*", re.IGNORECASE)
_fmcsa: FMCSAClient | None = None


def _get_fmcsa() -> FMCSAClient:
    global _fmcsa
    if _fmcsa is None:
        _fmcsa = FMCSAClient()
    return _fmcsa


def _normalize_mc(value: str) -> str:
    return MC_PREFIX.sub("", value.strip())


@router.post("/onboard", response_model=CarrierProfileOut)
async def onboard_carrier(
    body: CarrierProfileCreate,
    user_id: str = Depends(get_user_id),
):
    """Create a carrier profile by looking up the MC number in FMCSA."""
    mc = _normalize_mc(body.mc_number)
    if not mc.isdigit():
        raise HTTPException(status_code=400, detail="MC number must be numeric")

    fmcsa = _get_fmcsa()
    info = await fmcsa.lookup_mc(mc)
    if info is None:
        raise HTTPException(status_code=404, detail=f"No carrier found for MC {mc}")

    sb = get_supabase()

    existing = sb.table("carrier_profiles").select("id").eq("user_id", user_id).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Profile already exists. Use PATCH to update.")

    row = {
        "user_id": user_id,
        "mc_number": mc,
        "dot_number": info.dot_number,
        "legal_name": info.legal_name,
        "dba_name": info.dba_name,
        "allowed_to_operate": info.allowed_to_operate,
        "out_of_service": info.out_of_service,
        "home_city": info.city,
        "home_state": info.state,
        "telephone": info.telephone,
    }
    resp = sb.table("carrier_profiles").insert(row).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create profile")
    return CarrierProfileOut(**resp.data[0])


@router.get("/me", response_model=CarrierProfileOut)
async def get_my_profile(user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    resp = sb.table("carrier_profiles").select("*").eq("user_id", user_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="No profile found. Complete onboarding first.")
    return CarrierProfileOut(**resp.data[0])


@router.patch("/me", response_model=CarrierProfileOut)
async def update_my_profile(
    body: CarrierProfileUpdate,
    user_id: str = Depends(get_user_id),
):
    sb = get_supabase()
    updates = body.model_dump(exclude_none=True)
    if "preferred_lanes" in updates:
        updates["preferred_lanes"] = [lane.model_dump() if hasattr(lane, "model_dump") else lane for lane in updates["preferred_lanes"]]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    resp = (
        sb.table("carrier_profiles")
        .update(updates)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CarrierProfileOut(**resp.data[0])


@router.get("/{mc_number}")
async def lookup_carrier(mc_number: str):
    """Public FMCSA lookup (no auth required) — backwards compat with original service."""
    mc = _normalize_mc(mc_number)
    if not mc.isdigit():
        raise HTTPException(status_code=400, detail="MC number must be numeric")

    fmcsa = _get_fmcsa()
    info = await fmcsa.lookup_mc(mc)
    if info is None:
        raise HTTPException(status_code=404, detail=f"No carrier found for MC {mc}")
    return info
