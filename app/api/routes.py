from fastapi import APIRouter
from app.api.endpoints import hello, appointments, voice_loop

router = APIRouter()
router.include_router(hello.router, prefix="/hello", tags=["hello"])
router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
router.include_router(voice_loop.router, prefix="/voice-loop", tags=["voice-loop"])
