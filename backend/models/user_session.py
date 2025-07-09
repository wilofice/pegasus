"""User Session mapping model for session persistence."""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
from models.base import Base


class UserSession(Base):
    """Map user IDs to their active sessions."""
    
    __tablename__ = "user_sessions"
    
    user_id = Column(String, primary_key=True, nullable=False)
    session_id = Column(String, nullable=False)
    is_alive = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Add indexes for faster queries
    __table_args__ = (
        Index('idx_user_session_alive', 'user_id', 'is_alive'),
        Index('idx_session_id', 'session_id'),
    )
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, session_id={self.session_id}, is_alive={self.is_alive})>"