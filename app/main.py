from dotenv import load_dotenv

# Load environment variables from .env file before importing app modules.
load_dotenv()

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.config import settings

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Voice loop MVP with Modulate STT and blackbox LLM/TTS stubs",
)

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_str)

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "healthy"}
