from __future__ import annotations

import io
import math
import struct
import wave

from app.schemas.voice_loop import TTSResult


class BlackboxTTSClient:
    async def synthesize_speech(self, text: str, voice: str | None = None) -> TTSResult:
        _ = text
        _ = voice
        # Generates a short synthetic tone as a deterministic placeholder for real TTS output.
        sample_rate = 16000
        duration_sec = 1.2
        frequency_hz = 440.0
        amplitude = 0.3
        frame_count = int(sample_rate * duration_sec)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for i in range(frame_count):
                value = int(32767 * amplitude * math.sin(2 * math.pi * frequency_hz * (i / sample_rate)))
                wav_file.writeframesraw(struct.pack("<h", value))

        return TTSResult(
            audio_bytes=buffer.getvalue(),
            mime_type="audio/wav",
            provider="blackbox_tts_stub",
        )

