from __future__ import annotations

import asyncio
import base64
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx
from websockets.exceptions import ConnectionClosed
from google import genai
from google.genai import types
import logging

try:
    from elevenlabs import (
        AudioFormat,
        CommitStrategy,
        ElevenLabs,
        RealtimeAudioOptions,
        RealtimeEvents,
    )
except Exception:  # noqa: BLE001
    ElevenLabs = None  # type: ignore

from app.tools.grounding_tools import fetch_weather_context, search_sop_guidance
from app.tools.vector_grounding_tools import search_incident_knowledge
from app.tools.risk_tools import detect_hazard

logger = logging.getLogger(__name__)

@dataclass
class FallbackConfig:
    eleven_api_key: str
    eleven_voice_id: str
    eleven_tts_model: str
    fallback_model_id: str
    tts_output_format: str = "pcm_24000"


class ElevenFallbackEngine:
    def __init__(self, config: FallbackConfig, system_instruction: str) -> None:
        self.config = config
        self.system_instruction = system_instruction
        self._client = ElevenLabs(api_key=config.eleven_api_key) if ElevenLabs else None
        self._stt_conn = None
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()
        self._http = httpx.AsyncClient(timeout=20.0)
        self._last_assistant_text = ""
        self._stt_ready = asyncio.Event()
        self._last_image_bytes: bytes | None = None
        self._last_image_mime: str | None = None
        self._last_image_ts: float | None = None

    @property
    def ready(self) -> bool:
        return self._stt_ready.is_set()

    async def start(self) -> None:
        if not self._client:
            raise RuntimeError("elevenlabs sdk not installed")
        loop = asyncio.get_running_loop()
        self._stt_conn = await self._client.speech_to_text.realtime.connect(
            RealtimeAudioOptions(
                model_id="scribe_v2_realtime",
                audio_format=AudioFormat.PCM_16000,
                sample_rate=16000,
                commit_strategy=CommitStrategy.VAD,
                include_timestamps=False,
                vad_silence_threshold_secs=1.4,
                vad_threshold=0.4,
                min_speech_duration_ms=120,
                min_silence_duration_ms=120,
            )
        )
        logger.info("ElevenLabs STT connect() returned; awaiting session start.")

        def on_session_started(_: dict[str, Any]) -> None:
            self._stt_ready.set()
            logger.info("ElevenLabs STT session started.")

        def on_committed_transcript(data: dict[str, Any]) -> None:
            text = (data or {}).get("text") or ""
            if text:
                logger.info("ElevenLabs STT committed transcript (len=%d).", len(text))
                loop.call_soon_threadsafe(self._transcript_queue.put_nowait, text)

        def on_error(err: Any) -> None:
            logger.error("ElevenLabs STT error: %s", err)
            self._stt_ready.set()

        self._stt_conn.on(RealtimeEvents.SESSION_STARTED, on_session_started)
        self._stt_conn.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
        self._stt_conn.on(RealtimeEvents.ERROR, on_error)

        try:
            await asyncio.wait_for(self._stt_ready.wait(), timeout=6.0)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("ElevenLabs STT session did not start in time") from exc

    async def close(self) -> None:
        if self._stt_conn:
            await self._stt_conn.close()
        await self._http.aclose()

    async def send_audio(self, pcm16: bytes) -> None:
        if not self._stt_conn:
            logger.warning("ElevenLabs STT not connected; dropping audio.")
            return
        payload: dict[str, Any] = {
            "audio_base_64": base64.b64encode(pcm16).decode("utf-8"),
            "sample_rate": 16000,
        }
        try:
            await self._stt_conn.send(payload)
        except ConnectionClosed as exc:
            logger.warning("ElevenLabs STT websocket closed: %s", exc)

    def set_latest_image(self, image_bytes: bytes, mime_type: str) -> None:
        self._last_image_bytes = image_bytes
        self._last_image_mime = mime_type
        self._last_image_ts = time.time()

    async def next_transcript(self) -> str:
        return await self._transcript_queue.get()

    async def generate_response(self, text: str) -> str:
        tool_context = self._run_fallback_tools(text)
        prompt = (
            f"{self.system_instruction}\n\n"
            f"User said: {text}\n\n"
            f"Tool context (if any):\n{tool_context}\n\n"
            "Respond with concise operational guidance. Include Sources if tool context provides sources."
        )

        client = genai.Client()
        try:
            parts = [types.Part(text=prompt)]
            if self._last_image_bytes and self._last_image_mime:
                age = time.time() - (self._last_image_ts or 0)
                if age < 8:
                    parts.insert(
                        0,
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=self._last_image_mime,
                                data=self._last_image_bytes,
                            )
                        ),
                    )
            response = client.models.generate_content(
                model=self.config.fallback_model_id,
                contents=[types.Content(role="user", parts=parts)],
            )
            output = (response.text or "").strip()
            self._last_assistant_text = output
            return output
        except Exception as exc:  # noqa: BLE001
            logger.error("Fallback model error: %s", exc)
            return "Fallback model error. Please try again or switch to text input."

    async def synthesize_tts(self, text: str) -> bytes:
        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.config.eleven_voice_id}?output_format={self.config.tts_output_format}"
        )
        headers = {
            "xi-api-key": self.config.eleven_api_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.config.eleven_tts_model,
            "voice_settings": {"stability": 0.3, "similarity_boost": 0.7},
        }
        resp = await self._http.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.content

    def _run_fallback_tools(self, text: str) -> str:
        lower = text.lower()
        chunks: list[str] = []

        if any(k in lower for k in ["weather", "rain", "storm", "forecast"]):
            jurisdiction = "ng" if "nigeria" in lower or "lagos" in lower or "ibadan" in lower else ""
            location = "Lagos" if "lagos" in lower else "Nigeria" if jurisdiction else ""
            res = fetch_weather_context(jurisdiction=jurisdiction, location=location)
            chunks.append(f"[weather_context] {res}")

        if any(k in lower for k in ["sop", "procedure", "policy", "protocol"]):
            res = search_sop_guidance(text)
            chunks.append(f"[sop_guidance] {res}")

        if any(k in lower for k in ["incident", "crash", "collision", "emergency"]):
            res = search_incident_knowledge(query=text, jurisdiction="ng", doc_type="")
            chunks.append(f"[incident_knowledge] {res}")

        if any(k in lower for k in ["smoke", "fire", "sparks", "gas", "leak", "spill"]):
            res = detect_hazard(text)
            chunks.append(f"[hazard] {res}")

        return "\n".join(chunks) if chunks else "No tools triggered."


def build_fallback_config() -> FallbackConfig:
    return FallbackConfig(
        eleven_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        eleven_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
        eleven_tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"),
        fallback_model_id=os.getenv("FALLBACK_MODEL_ID", "gemini-2.5-flash"),
        tts_output_format=os.getenv("ELEVENLABS_TTS_FORMAT", "pcm_24000"),
    )
