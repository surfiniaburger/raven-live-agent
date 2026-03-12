import asyncio
import types
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.fallback import eleven_fallback as ef  # noqa: E402


class FakeConn:
    def __init__(self, trigger_session_started: bool = True) -> None:
        self._handlers = {}
        self._trigger_session_started = trigger_session_started

    def on(self, event, handler):
        self._handlers[event] = handler
        if self._trigger_session_started and event == ef.RealtimeEvents.SESSION_STARTED:
            handler({})

    async def send(self, payload):
        self.last_payload = payload

    async def close(self):
        return None


class FakeSpeechToText:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    async def connect(self, *_args, **_kwargs):
        return self._conn


class FakeElevenLabsClient:
    def __init__(self, conn: FakeConn) -> None:
        self.speech_to_text = types.SimpleNamespace(realtime=FakeSpeechToText(conn))


@pytest.mark.asyncio
async def test_build_fallback_config_env(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    monkeypatch.setenv("ELEVENLABS_TTS_MODEL", "m")
    monkeypatch.setenv("ELEVENLABS_TTS_FORMAT", "pcm_24000")
    monkeypatch.setenv("FALLBACK_MODEL_ID", "gemini-2.5-flash")

    cfg = ef.build_fallback_config()
    assert cfg.eleven_api_key == "k"
    assert cfg.eleven_voice_id == "v"
    assert cfg.eleven_tts_model == "m"
    assert cfg.tts_output_format == "pcm_24000"
    assert cfg.fallback_model_id == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_start_sets_ready(monkeypatch):
    conn = FakeConn(trigger_session_started=True)
    monkeypatch.setattr(ef, "ElevenLabs", lambda api_key: FakeElevenLabsClient(conn))
    monkeypatch.setattr(ef, "RealtimeEvents", types.SimpleNamespace(SESSION_STARTED="session_started", COMMITTED_TRANSCRIPT="committed", ERROR="error"))

    cfg = ef.FallbackConfig(
        eleven_api_key="k",
        eleven_voice_id="v",
        eleven_tts_model="m",
        fallback_model_id="gemini-2.5-flash",
    )
    engine = ef.ElevenFallbackEngine(cfg, system_instruction="test")
    await engine.start()
    assert engine.ready


@pytest.mark.asyncio
async def test_start_timeout(monkeypatch):
    conn = FakeConn(trigger_session_started=False)
    monkeypatch.setattr(ef, "ElevenLabs", lambda api_key: FakeElevenLabsClient(conn))
    monkeypatch.setattr(ef, "RealtimeEvents", types.SimpleNamespace(SESSION_STARTED="session_started", COMMITTED_TRANSCRIPT="committed", ERROR="error"))

    orig_wait_for = ef.asyncio.wait_for

    async def fast_wait_for(awaitable, timeout):
        return await orig_wait_for(awaitable, timeout=0.01)

    monkeypatch.setattr(ef.asyncio, "wait_for", fast_wait_for)

    cfg = ef.FallbackConfig(
        eleven_api_key="k",
        eleven_voice_id="v",
        eleven_tts_model="m",
        fallback_model_id="gemini-2.5-flash",
    )
    engine = ef.ElevenFallbackEngine(cfg, system_instruction="test")
    with pytest.raises(RuntimeError, match="session did not start"):
        await engine.start()
