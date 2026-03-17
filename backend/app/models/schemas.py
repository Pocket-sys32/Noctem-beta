from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, Field


# ── Carrier Profile ──────────────────────────────────────────

class Lane(BaseModel):
    origin: str
    destination: str


class CarrierProfileBase(BaseModel):
    mc_number: str
    dot_number: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    allowed_to_operate: bool = False
    out_of_service: bool = False
    safety_rating: str | None = None
    equipment_types: list[str] = Field(default_factory=list)
    preferred_lanes: list[Lane] = Field(default_factory=list)
    home_city: str | None = None
    home_state: str | None = None
    telephone: str | None = None


class CarrierProfileCreate(BaseModel):
    mc_number: str


class CarrierProfileUpdate(BaseModel):
    equipment_types: list[str] | None = None
    preferred_lanes: list[Lane] | None = None
    home_city: str | None = None
    home_state: str | None = None
    telephone: str | None = None


class CarrierProfileOut(CarrierProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


# ── Loads ────────────────────────────────────────────────────

class LoadOut(BaseModel):
    id: str
    origin_city: str
    origin_state: str
    origin_lat: float | None = None
    origin_lng: float | None = None
    dest_city: str
    dest_state: str
    dest_lat: float | None = None
    dest_lng: float | None = None
    equipment_type: str
    weight_lbs: int | None = None
    rate_per_mile: float | None = None
    total_rate: float | None = None
    miles: int | None = None
    pickup_date: date | None = None
    delivery_date: date | None = None
    broker_name: str | None = None
    broker_mc: str | None = None
    status: str = "available"


class ScoredLoad(LoadOut):
    fit_score: float = 0.0
    score_breakdown: dict = Field(default_factory=dict)
    market_summary: str | None = None


# ── Market ───────────────────────────────────────────────────

class MarketIndexOut(BaseModel):
    id: str
    region: str
    lat: float | None = None
    lng: float | None = None
    load_to_truck_ratio: float | None = None
    avg_rate_per_mile: float | None = None
    trend: str | None = None
    equipment_type: str | None = None
    computed_at: datetime | None = None


# ── Call Transcripts ─────────────────────────────────────────

class TranscriptEntry(BaseModel):
    role: str
    content: str
    timestamp: datetime | None = None


class CallTranscriptOut(BaseModel):
    id: str
    carrier_id: str
    twilio_call_sid: str | None = None
    language_detected: str | None = None
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    ai_summary: str | None = None
    actions_taken: list[dict] = Field(default_factory=list)
    duration_seconds: int | None = None
    created_at: datetime


# ── FMCSA (carried over from original service) ──────────────

class FMCSACarrierInfo(BaseModel):
    mc_number: str
    dot_number: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    allowed_to_operate: bool = False
    out_of_service: bool = False
    out_of_service_date: str | None = None
    city: str | None = None
    state: str | None = None
    telephone: str | None = None
