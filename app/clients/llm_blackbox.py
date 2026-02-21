from __future__ import annotations

from app.schemas.voice_loop import LLMRequest, LLMResponse


class BlackboxLLMClient:
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        # Stubbed by design for MVP. Keep deterministic for easy testing.
        _ = request
        return LLMResponse(
            text="Thanks for calling. I can help you schedule an appointment. What date and time work best for you?",
            tool_commands=[],
        )

