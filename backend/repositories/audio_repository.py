"""Repository for audio file database operations."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.audio_file import AudioFile, ProcessingStatus


class AudioRepository:
    """Repository for audio file database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: dict) -> AudioFile:
        """Create a new audio file record.
        
        Args:
            data: Dictionary with audio file data
            
        Returns:
            AudioFile: Created audio file instance
        """
        audio_file = AudioFile(**data)
        self.session.add(audio_file)
        await self.session.commit()
        await self.session.refresh(audio_file)
        return audio_file
    
    async def get_by_id(self, audio_id: UUID) -> Optional[AudioFile]:
        """Get audio file by ID.
        
        Args:
            audio_id: UUID of the audio file
            
        Returns:
            AudioFile or None if not found
        """
        result = await self.session.execute(
            select(AudioFile).where(AudioFile.id == audio_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user_id(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status: Optional[ProcessingStatus] = None
    ) -> List[AudioFile]:
        """Get audio files by user ID.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            status: Optional status filter
            
        Returns:
            List of AudioFile instances
        """
        query = select(AudioFile).where(AudioFile.user_id == user_id)
        
        if status:
            query = query.where(AudioFile.processing_status == status)
        
        query = query.order_by(desc(AudioFile.upload_timestamp))
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, audio_id: UUID, data: dict) -> Optional[AudioFile]:
        """Update audio file record.
        
        Args:
            audio_id: UUID of the audio file
            data: Dictionary with fields to update
            
        Returns:
            Updated AudioFile or None if not found
        """
        audio_file = await self.get_by_id(audio_id)
        if not audio_file:
            return None
        
        # Update fields
        for key, value in data.items():
            if hasattr(audio_file, key):
                setattr(audio_file, key, value)
        
        # Update timestamp
        audio_file.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(audio_file)
        return audio_file
    
    async def delete(self, audio_id: UUID) -> bool:
        """Delete audio file record.
        
        Args:
            audio_id: UUID of the audio file
            
        Returns:
            bool: True if deleted, False if not found
        """
        audio_file = await self.get_by_id(audio_id)
        if not audio_file:
            return False
        
        await self.session.delete(audio_file)
        await self.session.commit()
        return True
    
    async def list_with_filters(
        self,
        user_id: Optional[str] = None,
        status: Optional[ProcessingStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[AudioFile], int]:
        """List audio files with filters.
        
        Args:
            user_id: Optional user ID filter
            status: Optional status filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of AudioFile instances, total count)
        """
        # Build base query
        conditions = []
        
        if user_id:
            conditions.append(AudioFile.user_id == user_id)
        
        if status:
            conditions.append(AudioFile.processing_status == status)
        
        if from_date:
            conditions.append(AudioFile.upload_timestamp >= from_date)
        
        if to_date:
            conditions.append(AudioFile.upload_timestamp <= to_date)
        
        # Count query
        count_query = select(AudioFile)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        count_result = await self.session.execute(count_query)
        total_count = len(count_result.scalars().all())
        
        # Data query
        data_query = select(AudioFile)
        if conditions:
            data_query = data_query.where(and_(*conditions))
        
        data_query = data_query.order_by(desc(AudioFile.upload_timestamp))
        data_query = data_query.limit(limit).offset(offset)
        
        result = await self.session.execute(data_query)
        audio_files = result.scalars().all()
        
        return audio_files, total_count
    
    async def update_status(
        self,
        audio_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ) -> Optional[AudioFile]:
        """Update processing status of audio file.
        
        Args:
            audio_id: UUID of the audio file
            status: New processing status
            error_message: Optional error message
            
        Returns:
            Updated AudioFile or None if not found
        """
        update_data = {"processing_status": status}
        
        if error_message:
            update_data["error_message"] = error_message
        
        # Update timestamp based on status
        if status == ProcessingStatus.TRANSCRIBING:
            update_data["transcription_started_at"] = datetime.utcnow()
        elif status == ProcessingStatus.IMPROVING:
            update_data["transcription_completed_at"] = datetime.utcnow()
        elif status == ProcessingStatus.COMPLETED:
            update_data["improvement_completed_at"] = datetime.utcnow()
        
        return await self.update(audio_id, update_data)