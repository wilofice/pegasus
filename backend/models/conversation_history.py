"""Conversation history database model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import Base

class ConversationHistory(Base):
    """Conversation history database model."""
    
    __tablename__ = "conversation_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), index=True)
    user_id = Column(String(255), index=True)
    
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Metadata
    metadata = Column(JSONB)
