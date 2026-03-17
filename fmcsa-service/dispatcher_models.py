from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class EquipmentType(str, Enum):
    dry_van = "dry_van"
    reefer = "reefer"
    flatbed = "flatbed"


class SafetyRating(str, Enum):
    satisfactory = "satisfactory"
    conditional = "conditional"
    unsat = "unsat"
    unknown = "unknown"


class LanguageCode(str, Enum):
    en = "en"
    pa = "pa"
    es = "es"


class CarrierAuthorityStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"
    revoked = "revoked"
    unknown = "unknown"


class LanePreference(BaseModel):
    origin_region: str
    destination_region: str
    weight: float = Field(default=1.0, ge=0.0, le=5.0)


class ContactPreferences(BaseModel):
    preferred_phone: str | None = None
    notify_sms: bool = True
    notify_email: bool = True


class CarrierProfile(BaseModel):
    carrier_id: UUID = Field(default_factory=uuid4)
    mc_number: str
    company_name: str
    dot_number: str | None = None
    authority_status: CarrierAuthorityStatus = CarrierAuthorityStatus.unknown
    safety_rating: SafetyRating = SafetyRating.unknown
    equipment_types: list[EquipmentType] = Field(default_factory=list)
    operating_regions: list[str] = Field(default_factory=list)
    preferred_lanes: list[LanePreference] = Field(default_factory=list)
    rate_floor_per_mile: float = Field(default=2.0, ge=0)
    target_margin_pct: float = Field(default=18.0, ge=0, le=100)
    languages_supported: list[LanguageCode] = Field(
        default_factory=lambda: [LanguageCode.en, LanguageCode.pa, LanguageCode.es]
    )
    timezone: str = "America/Chicago"
    contact_preferences: ContactPreferences = Field(default_factory=ContactPreferences)
    profile_version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class CarrierProfilePatch(BaseModel):
    equipment_types: list[EquipmentType] | None = None
    operating_regions: list[str] | None = None
    preferred_lanes: list[LanePreference] | None = None
    rate_floor_per_mile: float | None = Field(default=None, ge=0)
    target_margin_pct: float | None = Field(default=None, ge=0, le=100)
    timezone: str | None = None
    contact_preferences: ContactPreferences | None = None
    languages_supported: list[LanguageCode] | None = None


class CarrierComplianceSnapshot(BaseModel):
    carrier_id: UUID
    source: str
    snapshot_time: datetime = Field(default_factory=utcnow)
    inspection_count_24m: int = 0
    oos_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    insurance_status: str = "unknown"
    safety_flags: list[str] = Field(default_factory=list)


class CarrierProfileEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    carrier_id: UUID
    event_type: str
    payload_json: dict[str, Any]
    profile_version: int
    emitted_at: datetime = Field(default_factory=utcnow)


class MarketRegion(BaseModel):
    region_id: str
    name: str
    polygon_geojson: dict[str, Any] | None = None
    timezone: str = "America/Chicago"


class MarketMetricsInterval(BaseModel):
    region_id: str
    interval_start: datetime
    interval_end: datetime
    load_count: int = 0
    truck_count: int = 0
    load_truck_ratio: float = 0.0
    avg_rate_per_mile: float = 0.0
    rate_momentum: float = 0.0
    rate_volatility_idx: float = 0.0
    hotness_index: float = Field(default=0.0, ge=0.0, le=100.0)


class LoadOpportunity(BaseModel):
    load_id: UUID = Field(default_factory=uuid4)
    origin_region_id: str
    destination_region_id: str
    equipment_required: EquipmentType
    pickup_time: datetime
    dropoff_time: datetime
    distance_miles: float = Field(gt=0)
    offered_rate: float = Field(gt=0)
    source: str = "mock_internal"


class BestFitScore(BaseModel):
    load_id: UUID
    carrier_id: UUID
    score_total: float = Field(ge=0.0, le=100.0)
    score_profile_fit: float = Field(ge=0.0, le=100.0)
    score_lane_fit: float = Field(ge=0.0, le=100.0)
    score_market_timing: float = Field(ge=0.0, le=100.0)
    score_profitability: float = Field(ge=0.0, le=100.0)
    explanation_json: dict[str, Any]
    computed_at: datetime = Field(default_factory=utcnow)


class NegotiationInsight(BaseModel):
    insight_id: UUID = Field(default_factory=uuid4)
    load_id: UUID
    carrier_id: UUID
    recommended_counter_rate: float = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_summary: str
    market_evidence_json: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)


class CallSession(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    carrier_id: UUID
    caller_number: str
    language_detected: LanguageCode
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class TranscriptTurn(BaseModel):
    session_id: UUID
    turn_index: int
    speaker: str
    text: str
    language: LanguageCode
    intent: str | None = None
    entities_json: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utcnow)


class ActionAudit(BaseModel):
    action_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | None = None
    actor_type: str
    action_name: str
    request_json: dict[str, Any]
    result_json: dict[str, Any]
    timestamp: datetime = Field(default_factory=utcnow)
