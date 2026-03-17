# Virtual Dispatcher MVP Architecture

## 1) Canonical Domain Contracts

The backend contracts are implemented in `dispatcher_models.py` and are designed around `CarrierProfile` as the central source of truth.

- `CarrierProfile`: identity, MC/DOT, authority, equipment, lane preferences, financial thresholds, languages, and monotonic `profile_version`.
- `CarrierProfilePatch`: controlled partial update contract for dashboard and voice mutations.
- `CarrierProfileEvent`: emitted for create/update to support realtime fanout and observability.
- `MarketMetricsInterval`: region/time metrics including load-truck ratio, volatility, and normalized `hotness_index`.
- `LoadOpportunity`: normalized mock load feed for matching and negotiation.
- `BestFitScore`: explainable ranking output with weighted dimensions and full explanation payload.
- `NegotiationInsight`: recommended counter rate, confidence, rationale, and evidence.
- `CallSession` + `TranscriptTurn` + `ActionAudit`: voice state, transcript history, and auditable action trail.

## 2) Realtime Sync Design (<=5s target)

`dispatcher_store.py` implements the synchronization model:

1. Profile write (`upsert_profile` or `patch_profile`) commits to operational store.
2. `CarrierProfileEvent` is published with `profile_version`.
3. Event fanout updates the in-memory realtime cache immediately.
4. Voice reads first check cache freshness (`<=5s`), then fallback to operational store.

This creates a deterministic write->event->cache flow with stale-read protection by version and time.

## 3) Multilingual Voice Orchestration

`dispatcher_voice.py` and `/voice/query` implement the phone-agent logic:

- Language detection for English (`en`), Punjabi (`pa`), and Spanish (`es`) using intent hints.
- Intent parsing for:
  - `get_best_load`
  - `update_preferred_lane`
- Profile-mutating intents require explicit confirmation.
- Every turn is persisted to transcripts and action audit logs.
- Voice endpoint uses the same profile object as dashboard APIs for shared context.

## 4) Dashboard MVP Data Endpoints

These endpoints support a Material Design 3 dashboard implementation:

- `GET /market/overview`: map heat source (`Market Overview` panel).
- `GET /loads/recommended/{carrier_id}`: top loads + profitability badges (`Recommended Loads` table).
- `GET /voice/status/{carrier_id}`: recent transcript turns and voice action logs (`Voice Agent Status` panel).
- `GET /carrier-profile/{carrier_id}/sync-status`: realtime consistency indicator.

## 5) Scoring and Intelligence Rules

`dispatcher_scoring.py` defines explainable phase-1 formulas.

- **Market Hotness Index**
  - `MHI = 0.5*norm(load_truck_ratio) + 0.3*norm(rate_momentum) + 0.2*norm(volatility_inverse)` scaled to 0-100.
- **Best Fit Score**
  - Weighted dimensions:
    - profile fit: 0.35
    - lane fit: 0.25
    - market timing: 0.20
    - profitability: 0.20
  - Includes explicit explanation payload for transparency.
- **Negotiation Insight**
  - Counter-rate generated from offered rate, market hotness uplift, and carrier margin floor.
  - Returns confidence and evidence fields for UI/tooling.

## 6) Delivery Phases and Targets

Phase and target contracts are exposed by `GET /delivery/phases`.

- **Phase 1 (MVP)**: MC onboarding, core profile/event system, mock market feeds, matching/negotiation, multilingual voice query, transcript panel APIs.
- **Phase 2**: external loadboard integration, model calibration, deeper dialect tuning, reliability hardening.
- **Targets**
  - Voice P95 response: <=2.5 seconds
  - Profile propagation: <=5 seconds
  - Market refresh interval: 1-5 minutes
