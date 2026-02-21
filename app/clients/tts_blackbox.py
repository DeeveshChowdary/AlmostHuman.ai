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
        sample_rate = 44100
        duration_sec = 1.8
        frequency_hz = 440.0
        amplitude = 0.55
        frame_count = int(sample_rate * duration_sec)

        frames = bytearray()
        for i in range(frame_count):
            value = int(32767 * amplitude * math.sin(2 * math.pi * frequency_hz * (i / sample_rate)))
            frames.extend(struct.pack("<h", value))

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(bytes(frames))

        return TTSResult(
            audio_bytes=buffer.getvalue(),
            mime_type="audio/wav",
            provider="blackbox_tts_stub",
        )
