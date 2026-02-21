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
    modulate_mock: bool = _to_bool(os.getenv("MODULATE_MOCK"), default=False)
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
    stt_prefer_streaming: bool = _to_bool(os.getenv("STT_PREFER_STREAMING"), default=True)
    speaker_diarization: bool = _to_bool(os.getenv("SPEAKER_DIARIZATION"), default=True)
    emotion_signal: bool = _to_bool(os.getenv("EMOTION_SIGNAL"), default=True)
    accent_signal: bool = _to_bool(os.getenv("ACCENT_SIGNAL"), default=True)
    pii_phi_tagging: bool = _to_bool(os.getenv("PII_PHI_TAGGING"), default=True)
    voice_loop_data_dir: str = os.getenv("VOICE_LOOP_DATA_DIR", ".data/voice_loop")
    mock_transcript_text: str = os.getenv(
        "MOCK_TRANSCRIPT_TEXT",
        "Hello, I need to schedule a dentist appointment next Tuesday morning.",
    )


settings = Settings()
