from fastapi import APIRouter
from app.api.endpoints import hello

router = APIRouter()
router.include_router(hello.router, prefix="/hello", tags=["hello"])
