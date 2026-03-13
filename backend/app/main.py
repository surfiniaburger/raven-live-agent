import asyncio
import base64
import json
import logging
import os
import warnings
from pathlib import Path

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
    from app.fallback.eleven_fallback import ElevenFallbackEngine, build_fallback_config
except ModuleNotFoundError:
    from agents.live_incident_agent import root_agent
    from safety.basic_guardrails import BasicGuardrailsPlugin
    from fallback.eleven_fallback import ElevenFallbackEngine, build_fallback_config

_dotenv_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_dotenv_path, override=True)
load_dotenv(override=True)

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

    async def send_mode_switch(mode: str, reason: str) -> None:
        payload = {
            "serverContent": {
                "modelTurn": {
                    "parts": [
                        {
                            "text": f"[SYSTEM:MODE_SWITCH] mode={mode} reason={reason}",
                        }
                    ]
                }
            }
        }
        await websocket.send_text(json.dumps(payload))

    async def send_interrupt() -> None:
        await websocket.send_text(json.dumps({"interrupted": True}))

    async def send_fallback_response(text: str, audio_bytes: bytes | None) -> None:
        parts = [{"text": text}]
        if audio_bytes:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "audio/pcm;rate=24000",
                        "data": base64.b64encode(audio_bytes).decode("utf-8"),
                    }
                }
            )
        payload = {
            "serverContent": {
                "modelTurn": {
                    "parts": parts,
                }
            }
        }
        await websocket.send_text(json.dumps(payload))

    mode_state = {"mode": "live"}
    interrupt_state = {"active": False}
    fallback_engine: ElevenFallbackEngine | None = None
    fallback_task: asyncio.Task | None = None

    async def upstream_task() -> None:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                return
            except RuntimeError:
                return
            if "bytes" in message:
                audio_bytes = message["bytes"]
                logger.info(
                    "Audio frame received: bytes=%d mode=%s",
                    len(audio_bytes),
                    mode_state["mode"],
                )
                if mode_state["mode"] == "fallback" and fallback_engine:
                    await fallback_engine.send_audio(audio_bytes)
                else:
                    audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=audio_bytes)
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
                if msg_type not in {"text", "audio", "image", "interrupt"}:
                    await send_system_warning("BAD_TYPE", f"Ignoring unsupported message type: {msg_type}")
                    continue

                if payload.get("type") == "interrupt":
                    if mode_state["mode"] == "fallback":
                        continue
                    interrupt_state["active"] = True
                    await send_interrupt()
                    continue

                if payload.get("type") == "text":
                    text_value = payload.get("text", "")
                    if not isinstance(text_value, str):
                        await send_system_warning("BAD_TEXT", "Expected string at payload.text.")
                        continue
                    if mode_state["mode"] == "fallback" and fallback_engine:
                        response_text = await fallback_engine.generate_response(text_value)
                        audio = await fallback_engine.synthesize_tts(response_text)
                        await send_fallback_response(response_text, audio)
                    else:
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
                    logger.info(
                        "Audio payload received: bytes=%d mode=%s",
                        len(audio_data),
                        mode_state["mode"],
                    )
                    if mode_state["mode"] == "fallback" and fallback_engine:
                        await fallback_engine.send_audio(audio_data)
                    else:
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
                    if mode_state["mode"] == "live":
                        live_request_queue.send_realtime(types.Blob(mime_type=mime_type, data=image_data))
                    elif fallback_engine:
                        fallback_engine.set_latest_image(image_data, mime_type)
                        logger.info("Image frame received for fallback: %s bytes", len(image_data))

    async def downstream_task() -> None:
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                await websocket.send_text(event.model_dump_json(exclude_none=True, by_alias=True))
        except WebSocketDisconnect:
            return

    async def fallback_loop() -> None:
        assert fallback_engine is not None
        while True:
            transcript = await fallback_engine.next_transcript()
            if not transcript:
                continue
            logger.info("Fallback STT commit: %s", transcript[:200])
            await send_system_warning("STT_COMMIT", transcript)
            response_text = await fallback_engine.generate_response(transcript)
            audio = await fallback_engine.synthesize_tts(response_text)
            if interrupt_state["active"]:
                interrupt_state["active"] = False
                continue
            await send_fallback_response(response_text, audio)

    upstream = asyncio.create_task(upstream_task())
    downstream = asyncio.create_task(downstream_task())
    try:
        done, pending = await asyncio.wait(
            [upstream, downstream],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        if downstream in done and downstream.exception():
            exc = downstream.exception()
            logger.error("Socket failure: %s", exc)
            error_text = str(exc).lower()
            fallback_trigger = (
                "1008" in error_text
                or "policy violation" in error_text
                or "timed out during opening handshake" in error_text
                or "timeout" in error_text
                or "oauth2.googleapis.com" in error_text
                or "transporterror" in error_text
                or "ssl" in error_text
            )
            if fallback_trigger:
                mode_state["mode"] = "fallback"
                reason = "live_model_policy_1008" if "1008" in error_text or "policy violation" in error_text else "live_model_handshake_timeout"
                await send_mode_switch("fallback", reason)
                cfg = build_fallback_config()
                if not cfg.eleven_api_key or not cfg.eleven_voice_id:
                    logger.error("Fallback disabled: ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID missing.")
                    await send_system_warning(
                        "FALLBACK_DISABLED",
                        "ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID missing; fallback voice unavailable.",
                    )
                else:
                    try:
                        fallback_engine = ElevenFallbackEngine(cfg, root_agent.instruction)
                        logger.info("Initializing fallback engine (ElevenLabs STT/TTS + %s).", cfg.fallback_model_id)
                        await fallback_engine.start()
                        logger.info("Fallback engine started.")
                        fallback_task = asyncio.create_task(fallback_loop())
                    except Exception as fallback_exc:  # noqa: BLE001
                        await send_system_warning(
                            "FALLBACK_INIT_FAILED",
                            f"Fallback init failed: {fallback_exc}",
                        )
                    wait_tasks = [upstream]
                    if fallback_task:
                        wait_tasks.append(fallback_task)
                    await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_EXCEPTION)
            else:
                raise exc
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        live_request_queue.close()
        if fallback_task:
            fallback_task.cancel()
        if fallback_engine:
            await fallback_engine.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
