from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.clients.llm_blackbox import BlackboxLLMClient
from app.clients.modulate_client import ModulateClient
from app.clients.tts_blackbox import BlackboxTTSClient
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
        llm_client=BlackboxLLMClient(),
        tts_client=BlackboxTTSClient(),
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
    if not settings.modulate_mock and not settings.modulate_api_key:
        raise HTTPException(status_code=400, detail="MODULATE_API_KEY is required when MODULATE_MOCK=0")

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


@router.get("/demo", response_class=HTMLResponse)
def voice_loop_demo() -> str:
    return """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Voice Loop Demo</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; max-width: 860px; }
      button { margin-right: 0.5rem; padding: 0.6rem 1rem; }
      pre { background: #f3f5f7; padding: 1rem; overflow: auto; }
    </style>
  </head>
  <body>
    <h2>Voice Loop Demo</h2>
    <p>Record audio from your device microphone and send it to Modulate STT.</p>
    <div>
      <button id="start">Start Recording</button>
      <button id="stop" disabled>Stop + Process</button>
      <button id="newSession">New Session</button>
    </div>
    <p><b>Session:</b> <span id="session">not started</span></p>
    <h3>Transcript + Signals</h3>
    <pre id="output">Waiting for input...</pre>
    <h3>Agent Audio</h3>
    <audio id="player" controls></audio>
    <script>
      let mediaRecorder;
      let chunks = [];
      let sessionId = null;

      async function startSession() {
        const r = await fetch('/api/v1/voice-loop/sessions/start', { method: 'POST' });
        const data = await r.json();
        sessionId = data.session_id;
        document.getElementById('session').innerText = sessionId;
      }

      document.getElementById('newSession').onclick = startSession;
      document.getElementById('start').onclick = async () => {
        if (!sessionId) await startSession();
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        chunks = [];
        mediaRecorder.ondataavailable = (event) => chunks.push(event.data);
        mediaRecorder.start();
        document.getElementById('start').disabled = true;
        document.getElementById('stop').disabled = false;
      };

      document.getElementById('stop').onclick = async () => {
        mediaRecorder.onstop = async () => {
          const blob = new Blob(chunks, { type: 'audio/webm' });
          const response = await fetch(`/api/v1/voice-loop/process?session_id=${encodeURIComponent(sessionId)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'audio/webm' },
            body: blob
          });
          const data = await response.json();
          document.getElementById('output').innerText = JSON.stringify(data, null, 2);

          if (data.tts_audio_b64 && data.tts_mime_type) {
            const audioSrc = `data:${data.tts_mime_type};base64,${data.tts_audio_b64}`;
            document.getElementById('player').src = audioSrc;
          }
        };

        mediaRecorder.stop();
        document.getElementById('start').disabled = false;
        document.getElementById('stop').disabled = true;
      };
    </script>
  </body>
</html>"""
