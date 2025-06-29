"""Audio file database model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, BigInteger, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base


class ProcessingStatus(str, enum.Enum):
    """Audio file processing status."""
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    IMPROVING = "improving"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioFile(Base):
    """Audio file database model."""
    
    __tablename__ = "audio_files"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(500), nullable=False, unique=True)
    file_size_bytes = Column(BigInteger)
    duration_seconds = Column(Float)
    mime_type = Column(String(100))
    
    # Transcription data
    original_transcript = Column(Text)
    improved_transcript = Column(Text)
    transcription_engine = Column(String(50))  # 'whisper' or 'deepgram'
    transcription_started_at = Column(DateTime)
    transcription_completed_at = Column(DateTime)
    improvement_completed_at = Column(DateTime)
    
    # Metadata
    user_id = Column(String(255), index=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    processing_status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
        index=True
    )
    error_message = Column(Text)
    
    # Tagging and categorization
    tag = Column(String(100), index=True)  # User-defined tag (e.g., "Work", "Family", "Groceries")
    category = Column(String(100), index=True)  # System category (optional)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "mime_type": self.mime_type,
            "original_transcript": self.original_transcript,
            "improved_transcript": self.improved_transcript,
            "transcription_engine": self.transcription_engine,
            "user_id": self.user_id,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "processing_status": self.processing_status.value if self.processing_status else None,
            "error_message": self.error_message,
            "tag": self.tag,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }