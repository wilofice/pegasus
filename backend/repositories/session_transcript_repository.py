"""Repository for managing session transcript tracking."""

import logging
from typing import Optional, List, Set
from datetime import datetime, timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from models.session_transcript import SessionTranscript
from .base import BaseRepository

logger = logging.getLogger(__name__)


class SessionTranscriptRepository(BaseRepository[SessionTranscript]):
    """Repository for session transcript operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(SessionTranscript, db)
    
    async def get_sent_transcripts(self, session_id: str) -> List[str]:
        """Get list of transcript IDs already sent in this session."""
        result = await self.db.execute(
            select(SessionTranscript.transcript_id).where(
                SessionTranscript.session_id == session_id,
                SessionTranscript.is_active == True
            )
        )
        return [row[0] for row in result.fetchall()]
    
    async def mark_transcript_sent(self, session_id: str, user_id: str, 
                                  transcript_id: str, content: Optional[str] = None) -> SessionTranscript:
        """Mark a transcript as sent in the current session."""
        sent_transcript = SessionTranscript(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            transcript_id=transcript_id,
            transcript_content=content[:500] if content else None,  # Store first 500 chars
            is_active=True
        )
        self.db.add(sent_transcript)
        await self.db.commit()
        await self.db.refresh(sent_transcript)
        
        logger.debug(f"Marked transcript {transcript_id} as sent in session {session_id}")
        return sent_transcript
    
    async def get_unsent_transcripts(self, session_id: str, all_transcript_ids: List[str]) -> List[str]:
        """Get transcript IDs that haven't been sent in the current session."""
        if not all_transcript_ids:
            return []
        
        # Get sent transcript IDs
        sent_ids = await self.get_sent_transcripts(session_id)
        sent_set = set(sent_ids)
        
        # Return only unsent transcripts
        unsent = [tid for tid in all_transcript_ids if tid not in sent_set]
        logger.debug(f"Session {session_id}: {len(unsent)} unsent transcripts out of {len(all_transcript_ids)}")
        return unsent
    
    async def deactivate_session_transcripts(self, session_id: str) -> int:
        """Mark all transcripts for a session as inactive."""
        result = await self.db.execute(
            update(SessionTranscript)
            .where(SessionTranscript.session_id == session_id)
            .values(is_active=False)
        )
        await self.db.commit()
        
        count = result.rowcount
        if count > 0:
            logger.info(f"Deactivated {count} transcripts for session {session_id}")
        return count
    
    async def cleanup_old_transcripts(self, days: int = 7) -> int:
        """Clean up transcript records older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(SessionTranscript).where(
                SessionTranscript.sent_at < cutoff_date
            )
        )
        
        old_records = result.scalars().all()
        for record in old_records:
            await self.db.delete(record)
        
        await self.db.commit()
        
        count = len(old_records)
        if count > 0:
            logger.info(f"Cleaned up {count} old transcript records")
        return count
    
    async def get_session_transcript_summary(self, session_id: str) -> dict:
        """Get summary of transcripts sent in a session."""
        result = await self.db.execute(
            select(SessionTranscript).where(
                SessionTranscript.session_id == session_id
            ).order_by(SessionTranscript.sent_at)
        )
        
        transcripts = result.scalars().all()
        
        return {
            "session_id": session_id,
            "total_sent": len(transcripts),
            "first_sent": transcripts[0].sent_at if transcripts else None,
            "last_sent": transcripts[-1].sent_at if transcripts else None,
            "transcript_ids": [t.transcript_id for t in transcripts]
        }