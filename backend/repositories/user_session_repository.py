"""Repository for managing user-session mappings."""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from models.user_session import UserSession
from .base import BaseRepository

logger = logging.getLogger(__name__)


class UserSessionRepository(BaseRepository[UserSession]):
    """Repository for user session operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(UserSession, db)
    
    async def get_active_session(self, user_id: str) -> Optional[UserSession]:
        """Get the active session for a user."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_alive == True
            )
        )
        return result.scalar_one_or_none()
    
    async def create_session(self, user_id: str, session_id: str) -> UserSession:
        """Create a new session for a user, marking previous sessions as inactive."""
        # First, mark all existing sessions for this user as inactive
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .values(is_alive=False, updated_at=datetime.utcnow())
        )
        
        # Create the new active session
        new_session = UserSession(
            user_id=user_id,
            session_id=session_id,
            is_alive=True
        )
        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(new_session)
        
        logger.info(f"Created new session {session_id} for user {user_id}")
        return new_session
    
    async def get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> UserSession:
        """Get existing active session or create a new one."""
        # Try to get existing active session
        existing = await self.get_active_session(user_id)
        if existing:
            logger.debug(f"Found existing session {existing.session_id} for user {user_id}")
            return existing
        
        # Create new session
        if not session_id:
            session_id = str(uuid.uuid4())
        
        return await self.create_session(user_id, session_id)
    
    async def deactivate_session(self, session_id: str) -> bool:
        """Mark a session as inactive."""
        result = await self.db.execute(
            update(UserSession)
            .where(UserSession.session_id == session_id)
            .values(is_alive=False, updated_at=datetime.utcnow())
        )
        await self.db.commit()
        
        affected = result.rowcount
        if affected > 0:
            logger.info(f"Deactivated session {session_id}")
        return affected > 0
    
    async def get_session_by_id(self, session_id: str) -> Optional[UserSession]:
        """Get a session by its ID."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up sessions older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            update(UserSession)
            .where(
                UserSession.updated_at < cutoff_date,
                UserSession.is_alive == False
            )
            .values(is_alive=False)
        )
        await self.db.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} old sessions")
        return count