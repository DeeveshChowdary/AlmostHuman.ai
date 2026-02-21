# AlmostHuman.ai

## Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management.

### 1. Install `uv`

If you haven't installed `uv` yet, you can do so using one of the following methods:

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
*(Alternatively, you can install it via pip: `pip install uv`)*

### 2. Install Project Dependencies

Run the following command in the project root to install the required dependencies using `uv` and ensure they are synchronized with the `uv.lock` file:

```bash
uv sync
```

### 3. Configure Environment

Create `.env` from `.env.example` and set your Modulate API key:

```bash
cp .env.example .env
```

Important environment flags:
- `MODULATE_STT_MOCK=0`: use real Modulate STT APIs
- `MODULATE_STT_MOCK=1`: use local STT mock
- `MODULATE_API_KEY`: required when `MODULATE_STT_MOCK=0`
- LLM/TTS are already blackbox stubs in current MVP

### 4. Run the Development Server

Start the FastAPI application with live reloading:

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at:
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Sample Endpoint:** [http://127.0.0.1:8000/api/v1/hello/](http://127.0.0.1:8000/api/v1/hello/)

## Voice Loop API

### Start Session

```bash
curl -X POST http://127.0.0.1:8000/api/v1/voice-loop/sessions/start
```

### Process Audio (STT -> signals -> LLM stub -> TTS stub)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/voice-loop/process \
  -H "Content-Type: audio/webm" \
  --data-binary "@/path/to/audio.webm"

# Optional existing session:
# http://127.0.0.1:8000/api/v1/voice-loop/process?session_id=<session-id>
```

Response includes:
- transcript and utterance-level Modulate signals (emotion/accent/language/speaker when available)
- derived signal bundle (intent, sentiment, risk flags, pace)
- LLM stub response text
- base64-encoded WAV audio from TTS stub (`tts_audio_b64`)

### Browser Mic Demo

Open:

`http://127.0.0.1:8000/api/v1/voice-loop/demo`

This page captures mic audio from your device, calls the backend voice loop endpoint, and plays returned audio.

### Fetch Session + Event Log

```bash
curl http://127.0.0.1:8000/api/v1/voice-loop/sessions/<session-id>
```
