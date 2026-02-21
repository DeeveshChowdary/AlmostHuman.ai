from __future__ import annotations

import base64
import logging
import uuid
from datetime import UTC, datetime

from app.clients.interfaces import LLMClientProtocol, ModulateClientProtocol, TTSClientProtocol
from app.schemas.voice_loop import (
    EmotionResult,
    IntentResult,
    LLMRequest,
    SignalBundle,
    StartSessionResponse,
    VoiceLoopProcessResponse,
)
from app.repositories.session_store import SessionStore

logger = logging.getLogger(__name__)


class VoiceLoopService:
    def __init__(
        self,
        modulate_client: ModulateClientProtocol,
        llm_client: LLMClientProtocol,
        tts_client: TTSClientProtocol,
        session_store: SessionStore,
    ) -> None:
        self.modulate_client = modulate_client
        self.llm_client = llm_client
        self.tts_client = tts_client
        self.session_store = session_store

    def start_session(self) -> StartSessionResponse:
        session_id = str(uuid.uuid4())
        self.session_store.create_session(session_id)
        self.session_store.append_event(session_id, "session_started", {})
        return StartSessionResponse(session_id=session_id, status="started")

    async def process_audio(
        self,
        audio_bytes: bytes,
        content_type: str,
        session_id: str | None = None,
    ) -> VoiceLoopProcessResponse:
        current_session_id = session_id or str(uuid.uuid4())
        if session_id is None:
            self.session_store.create_session(current_session_id)
        else:
            # Fail fast for unknown sessions before calling external providers.
            self.session_store.get_session(current_session_id)

        self.session_store.append_event(
            current_session_id,
            "audio_received",
            {
                "content_type": content_type,
                "size_bytes": len(audio_bytes),
            },
        )

        transcript = await self.modulate_client.transcribe(audio_bytes, content_type, current_session_id)
        self.session_store.append_event(
            current_session_id,
            "stt_completed",
            {
                "transport": transcript.transport,
                "text": transcript.text,
                "duration_ms": transcript.duration_ms,
                "utterance_count": len(transcript.utterances),
            },
        )

        intent = await self.modulate_client.analyze_intent(transcript.text, current_session_id)
        emotion = self._dominant_emotion(transcript) or await self.modulate_client.analyze_emotion(
            transcript.text,
            current_session_id,
        )

        signals = self._build_signals(intent=intent, emotion=emotion, transcript=transcript)
        llm_request = LLMRequest(transcript=transcript, signals=signals, session_id=current_session_id)
        llm_response = await self.llm_client.generate_response(llm_request)

        tts_result = await self.tts_client.synthesize_speech(llm_response.text)
        tts_audio_b64 = base64.b64encode(tts_result.audio_bytes).decode("ascii")

        turn_payload = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "user_text": transcript.text,
            "utterances": [item.model_dump() for item in transcript.utterances],
            "signals": signals.model_dump(),
            "agent_text": llm_response.text,
            "audio_mime_type": tts_result.mime_type,
            "audio_provider": tts_result.provider,
        }
        self.session_store.append_turn(current_session_id, turn_payload)
        self.session_store.append_event(
            current_session_id,
            "turn_completed",
            {
                "agent_text": llm_response.text,
                "audio_provider": tts_result.provider,
            },
        )

        logger.info(
            "Voice loop completed for session_id=%s, transport=%s, utterances=%d",
            current_session_id,
            transcript.transport,
            len(transcript.utterances),
        )

        return VoiceLoopProcessResponse(
            session_id=current_session_id,
            transcript=transcript,
            signals=signals,
            llm_response=llm_response,
            tts_audio_b64=tts_audio_b64,
            tts_mime_type=tts_result.mime_type,
            tts_provider=tts_result.provider,
            output_status="audio_generated",
        )

    def get_session(self, session_id: str) -> dict:
        record = self.session_store.get_session(session_id)
        events = self.session_store.load_events(session_id)
        return {
            "session": record.model_dump(),
            "events": events,
        }

    @staticmethod
    def _dominant_emotion(transcript) -> EmotionResult | None:
        emotions = [u.emotion for u in transcript.utterances if u.emotion]
        if not emotions:
            return None
        label = max(set(emotions), key=emotions.count)
        confidence = round(emotions.count(label) / len(emotions), 2)
        return EmotionResult(label=label, confidence=confidence, source="modulate_stt")

    def _build_signals(self, intent: IntentResult, emotion: EmotionResult, transcript) -> SignalBundle:
        utterances = transcript.utterances
        languages = sorted({u.language for u in utterances if u.language})
        accents = sorted({u.accent for u in utterances if u.accent})
        speakers = sorted({u.speaker for u in utterances if u.speaker is not None})
        pii_detected = any("<PII>" in u.text or "<PHI>" in u.text for u in utterances)
        speaking_pace_wpm = self._estimate_pace_wpm(transcript.text, transcript.duration_ms)

        sentiment = "neutral"
        if emotion.label in {"Happy", "Confident", "Relieved"}:
            sentiment = "positive"
        elif emotion.label in {"Angry", "Frustrated", "Concerned", "Sad", "Anxious"}:
            sentiment = "negative"

        lowered = transcript.text.lower()
        toxicity_risk = 0.05
        if any(word in lowered for word in ["stupid", "idiot", "hate"]):
            toxicity_risk = 0.7
        escalation_risk = 0.2
        if emotion.label in {"Angry", "Frustrated", "Anxious"}:
            escalation_risk = 0.65
        interruption_risk = 0.35 if len(speakers) > 1 else 0.1

        compliance_flags: list[str] = []
        if pii_detected:
            compliance_flags.append("pii_or_phi_detected")

        return SignalBundle(
            intent=intent,
            emotion=emotion,
            sentiment=sentiment,
            toxicity_risk=toxicity_risk,
            escalation_risk=escalation_risk,
            interruption_risk=interruption_risk,
            speaking_pace_wpm=speaking_pace_wpm,
            compliance_flags=compliance_flags,
            pii_detected=pii_detected,
            accents=accents,
            languages=languages,
            speakers=speakers,
            extra={"transport": transcript.transport},
        )

    @staticmethod
    def _estimate_pace_wpm(text: str, duration_ms: int) -> float | None:
        if duration_ms <= 0:
            return None
        words = len(text.split())
        minutes = duration_ms / 60000
        if minutes <= 0:
            return None
        return round(words / minutes, 2)
