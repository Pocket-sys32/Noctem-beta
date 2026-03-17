# Noctem — Virtual Dispatcher

AI-powered freight dispatch system with a web dashboard and multilingual voice agent.

## Architecture

```
NoctemMVP/
├── dashboard/          Next.js 14 + MUI + Supabase Auth + Mapbox
├── backend/            FastAPI — FMCSA, carrier profiles, load matching, market analysis
├── voice-server/       Twilio + OpenAI Realtime API WebSocket bridge
└── supabase/           SQL migrations (Postgres)
```

## Prerequisites

- Node.js 18+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A [Supabase](https://supabase.com) project
- API keys: FMCSA, OpenAI, Mapbox, Twilio

## Quick Start

### 1. Database

Run `supabase/migrations/001_initial.sql` in your Supabase SQL editor to create all tables and RLS policies. Then enable Google OAuth under Authentication → Providers.

### 2. Backend

```bash
cd backend
cp .env.example .env    # fill in your keys
uv run uvicorn app.main:app --reload
```

Seed mock data:
```bash
uv run python -m seed.seed_data
```

### 3. Dashboard

```bash
cd dashboard
cp .env.local.example .env.local    # fill in your keys
npm install
npm run dev
```

Open http://localhost:3000 — sign in with Google, enter your MC number, and explore.

### 4. Voice Server

```bash
cd voice-server
cp .env.example .env    # fill in your keys
uv run uvicorn server:app --port 5050
```

Expose with ngrok (`ngrok http 5050`) and set the webhook URL in your Twilio phone number config to `https://YOUR_NGROK/incoming-call`.

## Deploy

- **Dashboard** → Vercel (connect repo, set root to `dashboard/`, add env vars)
- **Backend** → Railway (set root to `backend/`, add env vars)
- **Voice Server** → Railway (set root to `voice-server/`, add env vars)

Update `NEXT_PUBLIC_BACKEND_URL` and `BACKEND_URL` to point to your Railway service URLs.

## Key Environment Variables

| Service | Variable | Description |
|---------|----------|-------------|
| Backend | `SUPABASE_URL` | Supabase project URL |
| Backend | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| Backend | `FMCSA_WEB_KEY` | FMCSA API key |
| Backend | `OPENAI_API_KEY` | OpenAI API key |
| Dashboard | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| Dashboard | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
| Dashboard | `NEXT_PUBLIC_BACKEND_URL` | Backend API URL |
| Dashboard | `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox GL access token |
| Voice | `OPENAI_API_KEY` | OpenAI API key |
| Voice | `BACKEND_URL` | Backend API URL |
