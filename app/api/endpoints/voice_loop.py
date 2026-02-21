from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.clients.llm_blackbox import BlackboxLLMClient
from app.clients.modulate_client import ModulateClient
from app.clients.tts_free import FreeTTSClient
from app.core.config import settings
from app.repositories.session_store import SessionStore
from app.schemas.voice_loop import StartSessionResponse, VoiceLoopProcessResponse
from app.services.voice_loop_service import VoiceLoopService

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_service() -> VoiceLoopService:
    session_store = SessionStore(settings.voice_loop_data_dir)
    return VoiceLoopService(
        modulate_client=ModulateClient(settings),
        llm_client=BlackboxLLMClient(session_store),
        tts_client=FreeTTSClient(settings),
        session_store=session_store,
    )


voice_loop_service = _build_service()


@router.post("/sessions/start", response_model=StartSessionResponse)
def start_voice_session() -> StartSessionResponse:
    return voice_loop_service.start_session()


@router.post("/process", response_model=VoiceLoopProcessResponse)
async def process_voice_input(
    request: Request,
    session_id: str | None = None,
) -> VoiceLoopProcessResponse:
    if not settings.modulate_api_key:
        raise HTTPException(status_code=400, detail="MODULATE_API_KEY is required")

    try:
        audio_bytes = await request.body()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="request body was empty")

        content_type = request.headers.get("content-type", "application/octet-stream")
        return await voice_loop_service.process_audio(
            audio_bytes=audio_bytes,
            content_type=content_type,
            session_id=session_id,
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown session_id: {session_id}") from None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Voice loop processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Voice loop processing failed: {exc}") from exc


@router.get("/sessions/{session_id}")
def get_voice_session(session_id: str) -> dict:
    try:
        return voice_loop_service.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from None


@router.post("/sessions/{session_id}/summary")
def generate_session_summary(session_id: str) -> dict:
    try:
        summary_payload = voice_loop_service.llm_client.generate_session_summary(session_id)
        return {
            "session_id": session_id,
            "summary": summary_payload.get("summary", "No prior context."),
            "conversation": summary_payload.get("conversation", {"turns": []}),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from None


@router.get("/demo")
def voice_loop_demo() -> FileResponse:
    ui_path = Path(__file__).resolve().parents[3] / "frontend" / "index.html"
    return FileResponse(str(ui_path))
