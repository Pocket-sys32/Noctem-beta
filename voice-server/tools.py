"""Tool definitions for the OpenAI Realtime API session.

Each tool maps to a handler on the FastAPI backend's /voice/tool-call endpoint.
"""

TOOLS = [
    {
        "type": "function",
        "name": "lookup_carrier",
        "description": (
            "Look up a trucking carrier by their MC number. Returns the carrier's name, "
            "authorization status, location, and DOT number."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mc_number": {
                    "type": "string",
                    "description": "The MC number to look up, e.g. '1015298' or 'MC-1015298'",
                },
            },
            "required": ["mc_number"],
        },
    },
    {
        "type": "function",
        "name": "get_recommended_loads",
        "description": (
            "Get the top recommended freight loads for the caller's carrier profile, "
            "ranked by AI fit score. Returns up to 3 best matches with route, rate, and equipment info."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "type": "function",
        "name": "update_preferred_lane",
        "description": (
            "Add a new preferred lane (origin-destination pair) to the carrier's profile. "
            "Both origin and destination should include city and state, e.g. 'Fresno, CA'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Lane origin city and state, e.g. 'Fresno, CA'",
                },
                "destination": {
                    "type": "string",
                    "description": "Lane destination city and state, e.g. 'Chicago, IL'",
                },
            },
            "required": ["origin", "destination"],
        },
    },
    {
        "type": "function",
        "name": "get_carrier_profile",
        "description": (
            "Retrieve the caller's carrier profile including company name, equipment types, "
            "preferred lanes, and home base."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "type": "function",
        "name": "link_with_pin",
        "description": (
            "Link this phone call to the caller's carrier profile using a 6-digit PIN generated in the dashboard. "
            "Call this first before personalized actions like recommending loads or updating lanes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pin": {
                    "type": "string",
                    "description": "6-digit PIN from the dashboard, e.g. '042913'",
                }
            },
            "required": ["pin"],
        },
    },
]

SYSTEM_PROMPT = """You are Noctem, an AI freight dispatcher assistant. You help trucking carriers find loads, check carrier credentials, and manage their dispatch profile.

KEY BEHAVIORS:
- Detect the caller's language from their first utterance. You MUST respond fluently in English, Spanish, or Punjabi — whichever the caller uses.
- If the caller speaks Punjabi, respond in Punjabi. If they speak Spanish, respond in Spanish. Match their language throughout the call.
- Be concise and professional. Truckers are busy — get to the point.
- When reporting loads, emphasize: route, equipment type, rate per mile, and total payout.
- Before any personalized requests (\"my loads\", \"update my lane\", \"my profile\"), you MUST link the call using a 6-digit PIN from the dashboard:
  1) Ask the caller for their 6-digit PIN
  2) Call link_with_pin(pin)
  3) If linking fails, ask them to generate a new PIN in the dashboard (Voice Agent panel) and try again.
- When a caller asks about a carrier, use lookup_carrier with their MC number.
- When they want load recommendations, use get_recommended_loads.
- When they want to add or change a preferred lane, use update_preferred_lane.
- You can also retrieve their full profile with get_carrier_profile.

MULTILINGUAL GREETINGS:
- English: "Hey, this is Noctem dispatch. How can I help you today?"
- Spanish: "Hola, soy Noctem dispatch. ¿En qué puedo ayudarte hoy?"
- Punjabi: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਇਹ Noctem dispatch ਹੈ। ਮੈਂ ਤੁਹਾਡੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?"

Start by greeting in English, then switch to the caller's language once detected."""
