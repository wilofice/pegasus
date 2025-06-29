"""Pydantic schemas for audio API responses."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from models.audio_file import ProcessingStatus


class AudioFileResponse(BaseModel):
    """Response schema for audio file details."""
    id: UUID
    filename: str
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    mime_type: Optional[str] = None
    original_transcript: Optional[str] = None
    improved_transcript: Optional[str] = None
    transcription_engine: Optional[str] = None
    transcription_started_at: Optional[datetime] = None
    transcription_completed_at: Optional[datetime] = None
    improvement_completed_at: Optional[datetime] = None
    user_id: Optional[str] = None
    upload_timestamp: Optional[datetime] = None
    processing_status: ProcessingStatus
    error_message: Optional[str] = None
    tag: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class AudioUploadResponse(BaseModel):
    """Response schema for audio file upload."""
    id: UUID
    filename: str
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    upload_timestamp: Optional[datetime] = None
    processing_status: ProcessingStatus
    message: str = "File uploaded successfully"

    class Config:
        use_enum_values = True


class AudioFileListResponse(BaseModel):
    """Response schema for listing audio files."""
    items: List[AudioFileResponse]
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Maximum number of items per page")
    offset: int = Field(..., description="Number of items skipped")
    
    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.offset + self.limit < self.total
    
    @property
    def page(self) -> int:
        """Current page number (1-indexed)."""
        return (self.offset // self.limit) + 1


class TranscriptResponse(BaseModel):
    """Response schema for transcript retrieval."""
    status: ProcessingStatus
    transcript: Optional[str] = None
    is_improved: bool = False
    transcription_engine: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class AudioProcessingStatusResponse(BaseModel):
    """Response schema for processing status updates."""
    id: UUID
    processing_status: ProcessingStatus
    error_message: Optional[str] = None
    transcription_started_at: Optional[datetime] = None
    transcription_completed_at: Optional[datetime] = None
    improvement_completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class AudioTagUpdateRequest(BaseModel):
    """Request schema for updating audio file tags."""
    tag: Optional[str] = Field(None, max_length=100, description="User-defined tag")
    category: Optional[str] = Field(None, max_length=100, description="System category")


class AudioTagsResponse(BaseModel):
    """Response schema for available tags and categories."""
    tags: List[str] = Field(description="Available user tags")
    categories: List[str] = Field(description="Available system categories")