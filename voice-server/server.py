"""Twilio ↔ OpenAI Realtime API bridge.

Twilio sends inbound call audio as a WebSocket Media Stream.
This server relays audio bidirectionally to the OpenAI Realtime API,
which handles speech-to-text, LLM reasoning, tool calls, and text-to-speech.

Run:
    cd voice-server
    uv run uvicorn server:app --port 5050
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse

from tools import TOOLS, SYSTEM_PROMPT

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

app = FastAPI(title="Noctem Voice Server")


@app.get("/")
async def index():
    return {"status": "ok", "service": "noctem-voice-server"}


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """Twilio webhook — returns TwiML that upgrades the call to a Media Stream."""
    host = request.headers.get("host", "localhost:5050")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://{host}/media-stream" />
    </Connect>
</Response>"""
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    """Bridge between Twilio Media Stream and OpenAI Realtime API."""
    await ws.accept()

    import websockets

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(OPENAI_REALTIME_URL, additional_headers=headers) as openai_ws:
        stream_sid: str | None = None
        carrier_id: str | None = None

        # Configure the OpenAI session
        session_config = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": "alloy",
                "instructions": SYSTEM_PROMPT,
                "modalities": ["text", "audio"],
                "temperature": 0.7,
                "tools": TOOLS,
            },
        }
        await openai_ws.send(json.dumps(session_config))

        async def twilio_to_openai():
            """Forward Twilio audio → OpenAI."""
            nonlocal stream_sid, carrier_id
            try:
                async for message in ws.iter_text():
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "start":
                        stream_sid = data["start"]["streamSid"]
                        custom = data["start"].get("customParameters", {})
                        carrier_id = custom.get("carrier_id")

                    elif event == "media":
                        payload = data["media"]["payload"]
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": payload,
                        }
                        await openai_ws.send(json.dumps(audio_append))

                    elif event == "stop":
                        break
            except Exception:
                pass

        async def openai_to_twilio():
            """Forward OpenAI audio → Twilio, and handle tool calls."""
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    event_type = data.get("type", "")

                    if event_type == "response.audio.delta" and stream_sid:
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": data["delta"]},
                        }
                        await ws.send_json(audio_delta)

                    elif event_type == "response.function_call_arguments.done":
                        carrier_id = await _handle_tool_call(data, openai_ws, carrier_id)

            except Exception:
                pass

        await asyncio.gather(twilio_to_openai(), openai_to_twilio())


async def _handle_tool_call(
    data: dict[str, Any],
    openai_ws: Any,
    carrier_id: str | None,
) -> str | None:
    """Execute a tool call against the backend and return results to OpenAI."""
    call_id = data.get("call_id", "")
    name = data.get("name", "")
    args_str = data.get("arguments", "{}")

    try:
        args = json.loads(args_str)
    except json.JSONDecodeError:
        args = {}

    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            f"{BACKEND_URL}/voice/tool-call",
            json={"tool": name, "args": args, "carrier_id": carrier_id},
        )
        result = resp.json().get("result", "Sorry, I couldn't process that.")

    # If the tool is link_with_pin, parse the carrier_id from the output so we can persist it for the call.
    if name == "link_with_pin" and isinstance(result, str) and "carrier_id:" in result:
        try:
            carrier_id = result.split("carrier_id:", 1)[1].strip()
        except Exception:
            pass

    # Send the tool result back to OpenAI Realtime
    tool_response = {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": result if isinstance(result, str) else json.dumps(result),
        },
    }
    await openai_ws.send(json.dumps(tool_response))

    # Trigger OpenAI to generate a spoken response based on the tool output
    await openai_ws.send(json.dumps({"type": "response.create"}))
    return carrier_id
