from __future__ import annotations

import logging

from app.core.config import Settings
from app.schemas.voice_loop import TTSResult
from app.clients.tts_blackbox import BlackboxTTSClient

try:
    import edge_tts  # type: ignore
except ImportError:  # pragma: no cover - environment-dependent
    edge_tts = None

logger = logging.getLogger(__name__)


class FreeTTSClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._fallback = BlackboxTTSClient()

    async def synthesize_speech(self, text: str, voice: str | None = None) -> TTSResult:
        if edge_tts is None:
            logger.warning("edge-tts not installed; falling back to blackbox TTS stub")
            return await self._fallback.synthesize_speech(text=text, voice=voice)

        selected_voice = voice or self.settings.free_tts_voice
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=self.settings.free_tts_rate,
                pitch=self.settings.free_tts_pitch,
                volume=self.settings.free_tts_volume,
            )

            audio_chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio_chunks.append(chunk["data"])

            audio_bytes = b"".join(audio_chunks)
            if not audio_bytes:
                raise RuntimeError("Free TTS returned empty audio payload.")

            return TTSResult(
                audio_bytes=audio_bytes,
                mime_type="audio/mpeg",
                provider="edge_tts_free",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("edge-tts failed; falling back to blackbox TTS stub: %s", exc)
            return await self._fallback.synthesize_speech(text=text, voice=voice)
