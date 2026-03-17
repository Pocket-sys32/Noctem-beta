"""Call transcript storage and retrieval routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth import get_user_id
from app.db import get_supabase
from app.models.schemas import CallTranscriptOut

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/", response_model=list[CallTranscriptOut])
async def list_transcripts(
    user_id: str = Depends(get_user_id),
    limit: int = Query(20, le=100),
):
    sb = get_supabase()
    profile_resp = sb.table("carrier_profiles").select("id").eq("user_id", user_id).execute()
    if not profile_resp.data:
        return []

    carrier_id = profile_resp.data[0]["id"]
    resp = (
        sb.table("call_transcripts")
        .select("*")
        .eq("carrier_id", carrier_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [CallTranscriptOut(**r) for r in (resp.data or [])]


@router.post("/", response_model=CallTranscriptOut)
async def create_transcript(
    body: dict,
):
    """Internal endpoint — called by the voice server to save a transcript."""
    sb = get_supabase()
    resp = sb.table("call_transcripts").insert(body).execute()
    if not resp.data:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to save transcript")
    return CallTranscriptOut(**resp.data[0])
