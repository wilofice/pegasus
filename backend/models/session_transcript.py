"""Session Transcript tracking model to avoid sending duplicate transcripts."""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from models.base import Base


class SessionTranscript(Base):
    """Track which transcripts have been sent in a session."""
    
    __tablename__ = "session_transcripts"
    
    id = Column(String, primary_key=True)  # UUID
    session_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    transcript_id = Column(String, nullable=False)  # Reference to audio file or transcript
    transcript_content = Column(Text, nullable=True)  # Store content hash or summary
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # Track if session is still active
    
    # Add indexes for efficient queries
    __table_args__ = (
        Index('idx_session_transcript', 'session_id', 'transcript_id'),
        Index('idx_user_session_active', 'user_id', 'session_id', 'is_active'),
        Index('idx_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f"<SessionTranscript(session_id={self.session_id}, transcript_id={self.transcript_id})>"