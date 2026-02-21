from __future__ import annotations

from app.schemas.voice_loop import LLMRequest, LLMResponse
from app.repositories.session_store import SessionStore
from app.services.appointment_manager import AppointmentManager
from app.core.database import AsyncSessionLocal
from app.repositories.conversation_repository import add_conversation


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

    async def generate_session_summary(self, session_id: str) -> dict:
        previous_messages = self._build_previous_messages(session_id)
        conversation_state = {
            "summary_generated": False,
            "conversation_summary": "No prior context.",
        }
        summary_text = self.appointment_manager.generate_summary(previous_messages, conversation_state)
        turns_json = self.appointment_manager.messages_as_turn_json(previous_messages)
        print("TURNS_JSON", json.dumps(turns_json, indent=4))
        
        await self.save_to_db(
            patient_phone=random.randint(1000000000, 9999999999),
            duration_seconds=random.randint(100, 1000),
            outcome=random.choice(["booked", "cancelled", "rescheduled"]),
            escalated=False,
            conversation_json=turns_json,
            isproceed=True 
        )

        appointment_manager = AppointmentManager()
        appointment_manager.get_improvement_insights(f"{turns_json.turns}")
        return turns_json

    async def save_to_db(self, **kwargs):
        """
        Helper method to save conversation to the database.
        Pass attributes like patient_phone, duration_seconds, outcome, conversation_json, etc.
        """
        async with AsyncSessionLocal() as db_session:
            return await add_conversation(session=db_session, **kwargs)

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
        return response
