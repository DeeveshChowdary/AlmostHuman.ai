from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from typing import Any
from urllib.parse import urlencode

import aiohttp

from app.core.config import Settings
from app.schemas.voice_loop import EmotionResult, IntentResult, TranscriptResult, TranscriptUtterance

logger = logging.getLogger(__name__)


class ModulateClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, audio_chunk: bytes, content_type: str, session_id: str) -> TranscriptResult:
        if self.settings.modulate_mock:
            return self._mock_transcript()

        if self.settings.stt_prefer_streaming:
            try:
                return await self._transcribe_streaming(audio_chunk, session_id=session_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Streaming STT failed for session %s; falling back to batch: %s",
                    session_id,
                    exc,
                )

        return await self._transcribe_batch(audio_chunk, content_type, session_id=session_id)

    async def analyze_intent(self, text: str, session_id: str) -> IntentResult:
        _ = session_id
        lowered = text.lower()
        if any(word in lowered for word in ["reschedule", "move appointment"]):
            return IntentResult(label="reschedule_appointment", confidence=0.84, reason="keyword_match")
        if any(word in lowered for word in ["cancel", "cancellation"]):
            return IntentResult(label="cancel_appointment", confidence=0.87, reason="keyword_match")
        if any(word in lowered for word in ["schedule", "book", "appointment"]):
            return IntentResult(label="schedule_appointment", confidence=0.9, reason="keyword_match")
        if any(word in lowered for word in ["confirm", "confirmation"]):
            return IntentResult(label="confirm_appointment", confidence=0.78, reason="keyword_match")
        return IntentResult(label="general_inquiry", confidence=0.55, reason="fallback")

    async def analyze_emotion(self, text: str, session_id: str) -> EmotionResult:
        _ = session_id
        lowered = text.lower()
        if any(word in lowered for word in ["angry", "upset", "frustrated"]):
            return EmotionResult(label="Frustrated", confidence=0.72, source="text_heuristic")
        if any(word in lowered for word in ["thanks", "great", "happy"]):
            return EmotionResult(label="Happy", confidence=0.67, source="text_heuristic")
        return EmotionResult(label="Neutral", confidence=0.6, source="text_heuristic")

    def summarize_utterance_signals(self, utterances: list[TranscriptUtterance]) -> dict[str, Any]:
        emotions = [u.emotion for u in utterances if u.emotion]
        accents = sorted({u.accent for u in utterances if u.accent})
        languages = sorted({u.language for u in utterances if u.language})
        speakers = sorted({u.speaker for u in utterances if u.speaker is not None})

        dominant_emotion = "Neutral"
        if emotions:
            dominant_emotion = Counter(emotions).most_common(1)[0][0]

        return {
            "dominant_emotion": dominant_emotion,
            "accents": accents,
            "languages": languages,
            "speakers": speakers,
        }

    async def _transcribe_streaming(self, audio_chunk: bytes, session_id: str) -> TranscriptResult:
        ws_url = self._ws_url()
        params = {
            "api_key": self.settings.modulate_api_key,
            "speaker_diarization": str(self.settings.speaker_diarization).lower(),
            "emotion_signal": str(self.settings.emotion_signal).lower(),
            "accent_signal": str(self.settings.accent_signal).lower(),
            "pii_phi_tagging": str(self.settings.pii_phi_tagging).lower(),
        }
        ws_url_with_query = f"{ws_url}?{urlencode(params)}"

        chunk_size = 8192
        utterances: list[TranscriptUtterance] = []
        raw_messages: list[dict[str, Any]] = []
        duration_ms = 0

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url_with_query) as ws:
                for idx in range(0, len(audio_chunk), chunk_size):
                    await ws.send_bytes(audio_chunk[idx : idx + chunk_size])
                await ws.send_str("")

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        payload = json.loads(msg.data)
                        raw_messages.append(payload)
                        msg_type = payload.get("type")
                        if msg_type == "utterance":
                            utterances.append(self._parse_utterance(payload["utterance"]))
                        elif msg_type == "done":
                            duration_ms = int(payload.get("duration_ms", 0))
                            break
                        elif msg_type == "error":
                            raise RuntimeError(payload.get("error", "unknown streaming stt error"))
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        raise RuntimeError(f"Websocket transport error in session {session_id}")

        text = " ".join(u.text for u in utterances).strip()
        return TranscriptResult(
            text=text,
            duration_ms=duration_ms,
            utterances=utterances,
            transport="streaming",
            raw_provider_payload={"messages": raw_messages},
        )

    async def _transcribe_batch(self, audio_chunk: bytes, content_type: str, session_id: str) -> TranscriptResult:
        url = self._http_url(self.settings.modulate_stt_batch_path)
        headers = {"X-API-Key": self.settings.modulate_api_key}
        form = aiohttp.FormData()
        ext = self._guess_extension(content_type)
        form.add_field(
            "upload_file",
            audio_chunk,
            filename=f"{session_id}.{ext}",
            content_type=content_type or "application/octet-stream",
        )
        form.add_field("speaker_diarization", str(self.settings.speaker_diarization).lower())
        form.add_field("emotion_signal", str(self.settings.emotion_signal).lower())
        form.add_field("accent_signal", str(self.settings.accent_signal).lower())
        form.add_field("pii_phi_tagging", str(self.settings.pii_phi_tagging).lower())

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form, timeout=90) as response:
                response_text = await response.text()
                if response.status != 200:
                    raise RuntimeError(f"Batch STT failed: status={response.status} body={response_text}")
                payload = json.loads(response_text)

        utterances = [self._parse_utterance(item) for item in payload.get("utterances", [])]
        return TranscriptResult(
            text=payload.get("text", ""),
            duration_ms=int(payload.get("duration_ms", 0)),
            utterances=utterances,
            transport="batch",
            raw_provider_payload=payload,
        )

    def _mock_transcript(self) -> TranscriptResult:
        utterance = TranscriptUtterance(
            utterance_uuid=str(uuid.uuid4()),
            text=self.settings.mock_transcript_text,
            start_ms=0,
            duration_ms=4200,
            speaker=1,
            language="en",
            emotion="Neutral",
            accent="American",
        )
        return TranscriptResult(
            text=self.settings.mock_transcript_text,
            duration_ms=4200,
            utterances=[utterance],
            transport="mock",
            raw_provider_payload={"mock": True},
        )

    def _parse_utterance(self, data: dict[str, Any]) -> TranscriptUtterance:
        return TranscriptUtterance(
            utterance_uuid=str(data.get("utterance_uuid", "")),
            text=str(data.get("text", "")),
            start_ms=int(data.get("start_ms", 0)),
            duration_ms=int(data.get("duration_ms", 0)),
            speaker=data.get("speaker"),
            language=data.get("language"),
            emotion=data.get("emotion"),
            accent=data.get("accent"),
        )

    def _http_url(self, path: str) -> str:
        return f"{self.settings.modulate_base_url.rstrip('/')}/{path.lstrip('/')}"

    def _ws_url(self) -> str:
        url = self._http_url(self.settings.modulate_stt_streaming_path)
        if url.startswith("https://"):
            return "wss://" + url[len("https://") :]
        if url.startswith("http://"):
            return "ws://" + url[len("http://") :]
        return url

    @staticmethod
    def _guess_extension(content_type: str) -> str:
        mapping = {
            "audio/ogg": "ogg",
            "audio/opus": "opus",
            "audio/wav": "wav",
            "audio/webm": "webm",
            "audio/mpeg": "mp3",
            "application/octet-stream": "opus",
        }
        return mapping.get(content_type or "application/octet-stream", "opus")

