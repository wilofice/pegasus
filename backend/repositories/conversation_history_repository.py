"""Repository for ConversationHistory model."""
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.conversation_history import ConversationHistory
from repositories.base_repository import BaseRepository

class ConversationHistoryRepository(BaseRepository[ConversationHistory]):
    """Repository for ConversationHistory model."""

    def __init__(self, db_session: AsyncSession):
        super().__init__(ConversationHistory, db_session)

    async def get_by_session_id(self, session_id: str) -> List[ConversationHistory]:
        """Get all conversation history for a given session ID."""
        result = await self.db_session.execute(
            select(self.model).filter(self.model.session_id == session_id).order_by(self.model.timestamp.asc())
        )
        return result.scalars().all()

    async def get_recent_for_user(self, user_id: str, days: int) -> List[ConversationHistory]:
        """Get recent conversation history for a given user ID."""
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.db_session.execute(
            select(self.model)
            .filter(self.model.user_id == user_id, self.model.timestamp >= since)
            .order_by(self.model.timestamp.asc())
        )
        return result.scalars().all()
