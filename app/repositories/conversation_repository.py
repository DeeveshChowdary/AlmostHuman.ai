import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation

async def add_conversation(
    session: AsyncSession,
    patient_phone: Optional[str] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
    duration_seconds: Optional[int] = None,
    resolution_type: Optional[str] = None,
    escalated: Optional[bool] = False,
    outcome: Optional[str] = None,
    conversation_json: Optional[List[Dict[str, Any]]] = None,
    isproceed: Optional[bool] = False,
) -> Conversation:
    """
    Helper method to asynchronously add a new Conversation record to the database.
    """
    new_convo = Conversation(
        id=uuid.uuid4(),
        patient_phone=patient_phone,
        started_at=started_at or datetime.now(UTC),
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        resolution_type=resolution_type,
        escalated=escalated,
        outcome=outcome,
        conversation_json=conversation_json,
        created_at=datetime.now(UTC),
        isproceed=isproceed,
    )
    
    session.add(new_convo)
    await session.commit()
    await session.refresh(new_convo)
    
    return new_convo
