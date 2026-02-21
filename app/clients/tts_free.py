from __future__ import annotations

from app.core.config import Settings
from app.schemas.voice_loop import TTSResult

try:
    import edge_tts  # type: ignore
except ImportError:  # pragma: no cover - environment-dependent
    edge_tts = None


class FreeTTSClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def synthesize_speech(self, text: str, voice: str | None = None) -> TTSResult:
        if edge_tts is None:
            raise RuntimeError("edge-tts is required for free TTS output. Install dependencies and retry.")

        selected_voice = voice or self.settings.free_tts_voice
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

