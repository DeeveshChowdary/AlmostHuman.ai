from fastapi import APIRouter
from app.api.endpoints import hello, appointments

router = APIRouter()
router.include_router(hello.router, prefix="/hello", tags=["hello"])
router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
