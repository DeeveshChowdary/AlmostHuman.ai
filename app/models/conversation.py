import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, Integer, Boolean, DateTime, cast, cast
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_phone = Column(String(20), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    resolution_type = Column(String(50), nullable=True)
    escalated = Column(Boolean, default=False, nullable=True)
    outcome = Column(String(50), nullable=True)
    
    # Store the actual array of JSON dicts representing the raw conversation log
    conversation_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    isproceed = Column(Boolean, default=False, nullable=True)
