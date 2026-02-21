from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscriptUtterance(BaseModel):
    utterance_uuid: str
    text: str
    start_ms: int = 0
    duration_ms: int = 0
    speaker: int | None = None
    language: str | None = None
    emotion: str | None = None
    accent: str | None = None


class TranscriptResult(BaseModel):
    text: str
    duration_ms: int = 0
    utterances: list[TranscriptUtterance] = Field(default_factory=list)
    transport: str = "unknown"
    raw_provider_payload: dict[str, Any] | None = None


class IntentResult(BaseModel):
    label: str
    confidence: float
    reason: str | None = None


class EmotionResult(BaseModel):
    label: str
    confidence: float
    source: str = "derived"


class SignalBundle(BaseModel):
    intent: IntentResult
    emotion: EmotionResult
    sentiment: str | None = None
    toxicity_risk: float | None = None
    escalation_risk: float | None = None
    interruption_risk: float | None = None
    speaking_pace_wpm: float | None = None
    compliance_flags: list[str] = Field(default_factory=list)
    pii_detected: bool = False
    accents: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    speakers: list[int] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(BaseModel):
    transcript: TranscriptResult
    signals: SignalBundle
    session_id: str


class ToolCommand(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    text: str
    tool_commands: list[ToolCommand] = Field(default_factory=list)


class TTSResult(BaseModel):
    audio_bytes: bytes
    mime_type: str
    provider: str


class StartSessionResponse(BaseModel):
    session_id: str
    status: str


class VoiceLoopProcessResponse(BaseModel):
    session_id: str
    transcript: TranscriptResult
    signals: SignalBundle
    llm_response: LLMResponse
    tts_audio_b64: str
    tts_mime_type: str
    tts_provider: str | None = None
    output_status: str


class SessionRecord(BaseModel):
    session_id: str
    created_at: str
    updated_at: str
    turns: list[dict[str, Any]] = Field(default_factory=list)
