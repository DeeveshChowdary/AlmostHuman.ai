from fastapi import APIRouter
from app.services.appointment_manager import AppointmentManager

router = APIRouter()
appointment_manager = AppointmentManager()

@router.get("/insights")
async def get_test_insights():
    """
    Test endpoint to fetch dummy improvement insights generated from transcripts.
    """
    insights = await appointment_manager.get_improvement_insights()
    return {"status": "success", "data": insights}
