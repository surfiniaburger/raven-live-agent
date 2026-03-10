import asyncio
import json
import logging
import os
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

try:
    from app.agents.live_incident_agent import root_agent
    from app.safety.basic_guardrails import BasicGuardrailsPlugin
except ModuleNotFoundError:
    from agents.live_incident_agent import root_agent
    from safety.basic_guardrails import BasicGuardrailsPlugin

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("websockets").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

PORT = 8080
APP_NAME = "raven-live-agent"

app = FastAPI(title="RAVEN Live Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
plugins = []
if os.getenv("ENABLE_BASIC_GUARDRAILS", "true").lower() == "true":
    plugins.append(BasicGuardrailsPlugin())

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
    plugins=plugins,
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": APP_NAME}


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str) -> None:
    await websocket.accept()
    logger.info("WebSocket connected: %s/%s", user_id, session_id)

    model_name = root_agent.model
    is_native_audio = "native-audio" in model_name.lower() or "live" in model_name.lower()

    run_config = None
    if is_native_audio:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
        )

    session = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)

    live_request_queue = LiveRequestQueue()
    live_request_queue.send_content(types.Content(parts=[types.Part(text="Hello")]))

    async def send_system_warning(code: str, detail: str) -> None:
        payload = {
            "serverContent": {
                "modelTurn": {
                    "parts": [
                        {
                            "text": f"[SYSTEM:{code}] {detail}",
                        }
                    ]
                }
            }
        }
        await websocket.send_text(json.dumps(payload))

    async def upstream_task() -> None:
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=message["bytes"])
                live_request_queue.send_realtime(audio_blob)
            elif "text" in message:
                try:
                    payload = json.loads(message["text"])
                except json.JSONDecodeError:
                    await send_system_warning("BAD_JSON", "Ignoring malformed JSON frame.")
                    continue

                if not isinstance(payload, dict):
                    await send_system_warning("BAD_PAYLOAD", "Ignoring non-object payload.")
                    continue

                msg_type = payload.get("type")
                if msg_type not in {"text", "audio", "image"}:
                    await send_system_warning("BAD_TYPE", f"Ignoring unsupported message type: {msg_type}")
                    continue

                if payload.get("type") == "text":
                    text_value = payload.get("text", "")
                    if not isinstance(text_value, str):
                        await send_system_warning("BAD_TEXT", "Expected string at payload.text.")
                        continue
                    live_request_queue.send_content(types.Content(parts=[types.Part(text=text_value)]))
                elif payload.get("type") == "audio":
                    import base64

                    audio_raw = payload.get("data", "")
                    if not isinstance(audio_raw, str) or not audio_raw:
                        await send_system_warning("BAD_AUDIO", "Expected base64 audio data.")
                        continue
                    try:
                        audio_data = base64.b64decode(audio_raw)
                    except Exception:  # noqa: BLE001
                        await send_system_warning("BAD_AUDIO", "Audio base64 decode failed.")
                        continue
                    live_request_queue.send_realtime(types.Blob(mime_type="audio/pcm;rate=16000", data=audio_data))
                elif payload.get("type") == "image":
                    import base64

                    image_raw = payload.get("data", "")
                    if not isinstance(image_raw, str) or not image_raw:
                        await send_system_warning("BAD_IMAGE", "Expected base64 image data.")
                        continue
                    try:
                        image_data = base64.b64decode(image_raw)
                    except Exception:  # noqa: BLE001
                        await send_system_warning("BAD_IMAGE", "Image base64 decode failed.")
                        continue
                    mime_type = payload.get("mimeType", "image/jpeg")
                    live_request_queue.send_realtime(types.Blob(mime_type=mime_type, data=image_data))

    async def downstream_task() -> None:
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            await websocket.send_text(event.model_dump_json(exclude_none=True, by_alias=True))

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as exc:
        logger.error("Socket failure: %s", exc)
    finally:
        live_request_queue.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
