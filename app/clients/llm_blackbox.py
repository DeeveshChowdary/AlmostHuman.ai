from __future__ import annotations

from app.schemas.voice_loop import LLMRequest, LLMResponse
from app.repositories.session_store import SessionStore
from app.services.appointment_manager import AppointmentManager
from app.clients.tts_free import FreeTTSClient
class BlackboxLLMClient:
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store
        self.appointment_manager = AppointmentManager()
        
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        session = self.session_store.get_session(request.session_id)
        
        previous_messages = []
        for turn in session.turns:
            if turn.get("user_text"):
                previous_messages.append({"role": "user", "content": turn["user_text"]})
            if turn.get("agent_text"):
                previous_messages.append({"role": "assistant", "content": turn["agent_text"]})
        
        conversation_state = {
            "summary_generated": False,
            "conversation_summary": "No prior context.",
        }
        
        result = await self.appointment_manager.answer_user(
            transcript_input=request.transcript.text,
            previous_messages=previous_messages,
            conversation_state=conversation_state,
        )
        
        print(result)
        
        response = LLMResponse(
            text=result["assistant_output"],
            tool_commands=[],
        )
        print(response)
        return response
        
        # return LLMResponse(
        #     text="Thanks for calling. I can help you schedule an appointment. What date and time work best for you?",
        #     tool_commands=[],
        # )
