from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    project_name: str = "AlmostHuman.ai API"
    version: str = "0.1.0"
    api_v1_str: str = "/api/v1"
    AIRIA_API_KEY_ANALYZER: str = os.getenv("AIRIA_API_KEY")
    modulate_api_key: str = os.getenv("MODULATE_API_KEY", "")
    modulate_base_url: str = os.getenv("MODULATE_BASE_URL", "https://modulate-prototype-apis.com")
    modulate_stt_streaming_path: str = os.getenv(
        "MODULATE_STT_STREAMING_PATH",
        "/api/velma-2-stt-streaming",
    )
    modulate_stt_batch_path: str = os.getenv(
        "MODULATE_STT_BATCH_PATH",
        "/api/velma-2-stt-batch",
    )
    modulate_tts_path: str = os.getenv("MODULATE_TTS_PATH", "/api/velma-2-tts")
    modulate_default_voice: str = os.getenv("MODULATE_DEFAULT_VOICE", "default")
    free_tts_voice: str = os.getenv("FREE_TTS_VOICE", "en-US-AriaNeural")
    free_tts_rate: str = os.getenv("FREE_TTS_RATE", "+0%")
    free_tts_pitch: str = os.getenv("FREE_TTS_PITCH", "+0Hz")
    free_tts_volume: str = os.getenv("FREE_TTS_VOLUME", "+0%")
    stt_prefer_streaming: bool = _to_bool(os.getenv("STT_PREFER_STREAMING"), default=True)
    speaker_diarization: bool = _to_bool(os.getenv("SPEAKER_DIARIZATION"), default=True)
    emotion_signal: bool = _to_bool(os.getenv("EMOTION_SIGNAL"), default=True)
    accent_signal: bool = _to_bool(os.getenv("ACCENT_SIGNAL"), default=True)
    pii_phi_tagging: bool = _to_bool(os.getenv("PII_PHI_TAGGING"), default=True)
    voice_loop_data_dir: str = os.getenv("VOICE_LOOP_DATA_DIR", ".data/voice_loop")


settings = Settings()
