const DEFAULT_BACKEND_URL = "http://localhost:8000";
const INLINED_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";

let _runtimeBackendUrl: string | null = null;

async function getBackendUrl(): Promise<string> {
  if (_runtimeBackendUrl) return _runtimeBackendUrl;

  // If the env var was inlined at build-time, use it.
  if (INLINED_BACKEND_URL) {
    _runtimeBackendUrl = INLINED_BACKEND_URL;
    return _runtimeBackendUrl;
  }

  // If we're in production and the env wasn't inlined, fetch runtime config from Next.js.
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    try {
      const res = await fetch("/api/config", { cache: "no-store" });
      const data = (await res.json()) as { backendUrl?: string };
      if (data.backendUrl) {
        _runtimeBackendUrl = data.backendUrl;
        return _runtimeBackendUrl;
      }
    } catch {
      // fall back below
    }
  }

  _runtimeBackendUrl = DEFAULT_BACKEND_URL;
  return _runtimeBackendUrl;
}

async function getAuthHeader(): Promise<Record<string, string>> {
  const { createClient } = await import("./supabase");
  const sb = createClient();
  const {
    data: { session },
  } = await sb.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    ...(await getAuthHeader()),
    ...init?.headers,
  };
  const backendUrl = await getBackendUrl();
  const res = await fetch(`${backendUrl}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Carriers ──────────────────────────────────────────────────

export interface Lane {
  origin: string;
  destination: string;
}

export interface CarrierProfile {
  id: string;
  user_id: string;
  mc_number: string;
  dot_number: string | null;
  legal_name: string | null;
  dba_name: string | null;
  allowed_to_operate: boolean;
  out_of_service: boolean;
  safety_rating: string | null;
  equipment_types: string[];
  preferred_lanes: Lane[];
  home_city: string | null;
  home_state: string | null;
  telephone: string | null;
  created_at: string;
  updated_at: string;
}

export function onboardCarrier(mc_number: string) {
  return apiFetch<CarrierProfile>("/carriers/onboard", {
    method: "POST",
    body: JSON.stringify({ mc_number }),
  });
}

export function getMyProfile() {
  return apiFetch<CarrierProfile>("/carriers/me");
}

export function updateMyProfile(data: {
  equipment_types?: string[];
  preferred_lanes?: Lane[];
}) {
  return apiFetch<CarrierProfile>("/carriers/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ── Loads ─────────────────────────────────────────────────────

export interface ScoredLoad {
  id: string;
  origin_city: string;
  origin_state: string;
  origin_lat: number | null;
  origin_lng: number | null;
  dest_city: string;
  dest_state: string;
  dest_lat: number | null;
  dest_lng: number | null;
  equipment_type: string;
  weight_lbs: number | null;
  rate_per_mile: number | null;
  total_rate: number | null;
  miles: number | null;
  pickup_date: string | null;
  delivery_date: string | null;
  broker_name: string | null;
  status: string;
  fit_score: number;
  score_breakdown: Record<string, number>;
  market_summary: string | null;
}

export function getRecommendedLoads(limit = 20) {
  return apiFetch<ScoredLoad[]>(`/loads/recommended?limit=${limit}`);
}

export function listLoads(params?: {
  status?: string;
  equipment_type?: string;
  origin_state?: string;
}) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return apiFetch<ScoredLoad[]>(`/loads/?${qs}`);
}

// ── Market ────────────────────────────────────────────────────

export interface MarketIndex {
  id: string;
  region: string;
  lat: number | null;
  lng: number | null;
  load_to_truck_ratio: number | null;
  avg_rate_per_mile: number | null;
  trend: string | null;
  equipment_type: string | null;
  computed_at: string | null;
}

export function getMarketIndices() {
  return apiFetch<MarketIndex[]>("/market/");
}

export function refreshMarketIndices() {
  return apiFetch<MarketIndex[]>("/market/refresh", { method: "POST" });
}

// ── Call Transcripts ──────────────────────────────────────────

export interface CallTranscript {
  id: string;
  carrier_id: string;
  twilio_call_sid: string | null;
  language_detected: string | null;
  transcript: { role: string; content: string; timestamp: string | null }[];
  ai_summary: string | null;
  actions_taken: Record<string, unknown>[];
  duration_seconds: number | null;
  created_at: string;
}

export function getTranscripts(limit = 20) {
  return apiFetch<CallTranscript[]>(`/transcripts/?limit=${limit}`);
}

// ── Voice PIN Linking ─────────────────────────────────────────

export interface VoicePin {
  pin: string;
  expires_at: string;
  carrier_id: string;
}

export function createVoicePin() {
  return apiFetch<VoicePin>("/pins/voice", { method: "POST" });
}
