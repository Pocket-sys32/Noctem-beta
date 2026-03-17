# Noctem Demo — MC Number Lookup

## What this demo does

A caller asks the voice agent to look up a trucking carrier by their MC number. The agent calls this server, which hits the FMCSA database and returns real carrier data.

The server now also includes a Virtual Dispatcher MVP backend:

- Carrier onboarding from MC number into a persistent `CarrierProfile`
- Mock market metrics ingestion + `Market Hotness Index`
- Best-fit load ranking + negotiation guidance
- Multilingual voice query flow (English, Punjabi, Spanish)
- Dashboard-supporting data endpoints for market overview, recommendations, and transcript status

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- [ngrok](https://ngrok.com) installed and authed (`ngrok config add-authtoken YOUR_TOKEN`)
- A `.env` file in this directory with a free FMCSA API key — register at [mobile.fmcsa.dot.gov](https://mobile.fmcsa.dot.gov/QCDevsite/docs/apiAccess) via Login.gov, then get your key under "My WebKeys":

```
FMCSA_WEB_KEY=your_key_here
```

---

## Running the server

```bash
uv run uvicorn main:app --reload
```

Server runs on `http://localhost:8000`.

---

## Exposing it for Vapi (ngrok)

Vapi needs a public URL to send tool calls to. In a second terminal:

```bash
ngrok http 80
```

Copy the `https://xxxx.ngrok-free.app` URL. You'll need it in the Vapi setup below.

---

## Vapi setup — what to configure

In the Vapi dashboard, add a **server tool** to your assistant with this definition:

```json
{
  "type": "function",
  "function": {
    "name": "lookup_mc",
    "description": "Look up a trucking carrier by their MC number. Returns the carrier's name, whether they are authorized to operate, and their location.",
    "parameters": {
      "type": "object",
      "properties": {
        "mc_number": {
          "type": "string",
          "description": "The MC number to look up, digits only or with MC prefix, e.g. '123456' or 'MC-123456'"
        }
      },
      "required": ["mc_number"]
    }
  },
  "server": {
    "url": "https://YOUR_NGROK_URL/tool-call"
  }
}
```

Replace `YOUR_NGROK_URL` with the ngrok URL from above.

Also add this to your assistant's system prompt:

> If a trucker asks about a carrier or wants to verify a load, ask for the MC number and use lookup_mc to check it. Read back the carrier name, whether they're authorized to operate, and where they're based.

---

## Testing without Vapi

Hit the REST endpoint directly:

```bash
# Real carrier (use this for demo)
curl http://localhost:8000/carriers/1015298

# With MC prefix (as a trucker might say it)
curl http://localhost:8000/carriers/MC-1015298

# Not found
curl http://localhost:8000/carriers/999999999

# Bad input
curl http://localhost:8000/carriers/abc
```

Virtual Dispatcher flow:

```bash
# 1) Onboard a carrier profile from MC number
curl -X POST http://localhost:8000/onboarding/mc \
  -H "Content-Type: application/json" \
  -d "{\"mc_number\":\"1015298\"}"

# 2) Upsert market metrics
curl -X POST http://localhost:8000/market/metrics \
  -H "Content-Type: application/json" \
  -d "{\"region_id\":\"manteca_ca\",\"load_count\":125,\"truck_count\":34,\"avg_rate_per_mile\":2.95,\"rate_momentum\":0.18,\"rate_volatility_idx\":0.22}"

# 3) Add a mock load
curl -X POST http://localhost:8000/loads \
  -H "Content-Type: application/json" \
  -d "{\"origin_region_id\":\"manteca_ca\",\"destination_region_id\":\"chicago\",\"equipment_required\":\"dry_van\",\"pickup_time\":\"2026-03-17T16:00:00Z\",\"dropoff_time\":\"2026-03-19T08:00:00Z\",\"distance_miles\":2100,\"offered_rate\":5200,\"source\":\"mock_internal\"}"

# 4) Get recommendations
curl http://localhost:8000/loads/recommended/CARRIER_ID_HERE

# 5) Query voice assistant behavior
curl -X POST http://localhost:8000/voice/query \
  -H "Content-Type: application/json" \
  -d "{\"carrier_id\":\"CARRIER_ID_HERE\",\"caller_number\":\"+15555550123\",\"utterance\":\"what is the best load near me right now\"}"
```

---

## What the agent will say

When a caller says *"can you check MC 1015298"*, the agent responds:

> "AA PRIME INC is authorized to operate. Based in MIAMI, FL. Their DOT number is 3235587."

Or if out of service:

> "ABC TRUCKING is NOT authorized to operate. They are currently out of service. Based in DALLAS, TX."

---

## What this is not (scope)

- No load board data (DAT API requires a commercial relationship — separate problem)
- No negotiation (different product entirely)
- No trucker memory/profile yet (next backend piece after this)
