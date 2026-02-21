from __future__ import annotations

from typing import Protocol

from app.schemas.voice_loop import (
    EmotionResult,
    IntentResult,
    LLMRequest,
    LLMResponse,
    TTSResult,
    TranscriptResult,
)


class ModulateClientProtocol(Protocol):
    async def transcribe(self, audio_chunk: bytes, content_type: str, session_id: str) -> TranscriptResult:
        ...

    async def analyze_intent(self, text: str, session_id: str) -> IntentResult:
        ...

    async def analyze_emotion(self, text: str, session_id: str) -> EmotionResult:
        ...


class LLMClientProtocol(Protocol):
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        ...


class TTSClientProtocol(Protocol):
    async def synthesize_speech(self, text: str, voice: str | None = None) -> TTSResult:
        ...

