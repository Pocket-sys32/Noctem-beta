from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID

from dispatcher_models import (
    ActionAudit,
    BestFitScore,
    CallSession,
    CarrierProfile,
    CarrierProfileEvent,
    CarrierProfilePatch,
    LoadOpportunity,
    MarketMetricsInterval,
    NegotiationInsight,
    TranscriptTurn,
)


class DispatcherStore:
    """In-memory operational store with event fanout for MVP."""

    def __init__(self):
        self._lock = Lock()
        self.profiles: dict[UUID, CarrierProfile] = {}
        self.profiles_by_mc: dict[str, UUID] = {}
        self.profile_cache: dict[UUID, CarrierProfile] = {}
        self.cache_updated_at: dict[UUID, datetime] = {}
        self.profile_events: list[CarrierProfileEvent] = []
        self.market_metrics: dict[str, MarketMetricsInterval] = {}
        self.loads: dict[UUID, LoadOpportunity] = {}
        self.best_fit_scores: list[BestFitScore] = []
        self.negotiation_insights: list[NegotiationInsight] = []
        self.sessions: dict[UUID, CallSession] = {}
        self.transcripts: list[TranscriptTurn] = []
        self.audit_log: list[ActionAudit] = []

    def upsert_profile(self, profile: CarrierProfile, event_type: str) -> CarrierProfile:
        with self._lock:
            existing_id = self.profiles_by_mc.get(profile.mc_number)
            if existing_id is not None and existing_id != profile.carrier_id:
                profile.carrier_id = existing_id

            previous = self.profiles.get(profile.carrier_id)
            if previous:
                profile.profile_version = previous.profile_version + 1
                profile.created_at = previous.created_at
            profile.updated_at = datetime.now(UTC)

            self.profiles[profile.carrier_id] = profile
            self.profiles_by_mc[profile.mc_number] = profile.carrier_id
            self._publish_profile_event(profile, event_type=event_type)
            return profile

    def get_profile(self, carrier_id: UUID) -> CarrierProfile | None:
        profile = self.profile_cache.get(carrier_id)
        if profile:
            cache_age = datetime.now(UTC) - self.cache_updated_at.get(carrier_id, datetime.min.replace(tzinfo=UTC))
            if cache_age <= timedelta(seconds=5):
                return profile

        with self._lock:
            profile = self.profiles.get(carrier_id)
            if profile:
                self.profile_cache[carrier_id] = profile
                self.cache_updated_at[carrier_id] = datetime.now(UTC)
            return profile

    def get_profile_by_mc(self, mc_number: str) -> CarrierProfile | None:
        carrier_id = self.profiles_by_mc.get(mc_number)
        if not carrier_id:
            return None
        return self.get_profile(carrier_id)

    def patch_profile(self, carrier_id: UUID, patch: CarrierProfilePatch) -> CarrierProfile | None:
        with self._lock:
            profile = self.profiles.get(carrier_id)
            if not profile:
                return None
            updates = patch.model_dump(exclude_none=True)
            merged = profile.model_copy(update=updates)
            merged.profile_version = profile.profile_version + 1
            merged.updated_at = datetime.now(UTC)
            self.profiles[carrier_id] = merged
            self._publish_profile_event(merged, event_type="CarrierProfileUpdated")
            return merged

    def _publish_profile_event(self, profile: CarrierProfile, event_type: str) -> None:
        event = CarrierProfileEvent(
            carrier_id=profile.carrier_id,
            event_type=event_type,
            payload_json=profile.model_dump(mode="json"),
            profile_version=profile.profile_version,
        )
        self.profile_events.append(event)
        # Immediate fanout to realtime cache for <=5s read freshness.
        self.profile_cache[profile.carrier_id] = profile
        self.cache_updated_at[profile.carrier_id] = datetime.now(UTC)

    def upsert_market_metrics(self, metrics: MarketMetricsInterval) -> MarketMetricsInterval:
        with self._lock:
            self.market_metrics[metrics.region_id] = metrics
            return metrics

    def add_load(self, load: LoadOpportunity) -> LoadOpportunity:
        with self._lock:
            self.loads[load.load_id] = load
            return load

    def add_score(self, score: BestFitScore) -> None:
        with self._lock:
            self.best_fit_scores.append(score)

    def add_negotiation(self, insight: NegotiationInsight) -> None:
        with self._lock:
            self.negotiation_insights.append(insight)

    def add_session(self, session: CallSession) -> None:
        with self._lock:
            self.sessions[session.session_id] = session

    def add_transcript_turn(self, turn: TranscriptTurn) -> None:
        with self._lock:
            self.transcripts.append(turn)

    def add_audit(self, audit: ActionAudit) -> None:
        with self._lock:
            self.audit_log.append(audit)

    def latest_transcripts(self, carrier_id: UUID, limit: int = 20) -> list[TranscriptTurn]:
        session_ids = {s.session_id for s in self.sessions.values() if s.carrier_id == carrier_id}
        turns = [t for t in self.transcripts if t.session_id in session_ids]
        return sorted(turns, key=lambda item: item.timestamp, reverse=True)[:limit]
