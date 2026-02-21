from __future__ import annotations

from app.schemas.voice_loop import LLMRequest, LLMResponse
from app.repositories.session_store import SessionStore
from app.services.appointment_manager import AppointmentManager


class BlackboxLLMClient:
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store
        self.appointment_manager = AppointmentManager()

    def _build_previous_messages(self, session_id: str) -> list[dict]:
        session = self.session_store.get_session(session_id)
        previous_messages: list[dict] = []
        for turn in session.turns:
            if turn.get("user_text"):
                previous_messages.append({"role": "user", "content": turn["user_text"]})
            if turn.get("agent_text"):
                previous_messages.append({"role": "assistant", "content": turn["agent_text"]})
        return previous_messages

    def generate_session_summary(self, session_id: str) -> str:
        previous_messages = self._build_previous_messages(session_id)
        conversation_state = {
            "summary_generated": False,
            "conversation_summary": "No prior context.",
        }
        return self.appointment_manager.generate_summary(previous_messages, conversation_state)

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        previous_messages = self._build_previous_messages(request.session_id)
        conversation_state = {
            "summary_generated": False,
            "conversation_summary": "No prior context.",
        }

        result = await self.appointment_manager.answer_user(
            transcript_input=request.transcript.text,
            previous_messages=previous_messages,
            conversation_state=conversation_state,
        )

        response = LLMResponse(
            text=result["assistant_output"],
            tool_commands=[],
        )
        print("response: ", result)
        return response
