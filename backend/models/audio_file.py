"""Audio file database model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, BigInteger, Text, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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
    language = Column(String(10), default='en', index=True)  # Language code (e.g., 'en', 'fr')
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
    
    # Brain indexing status
    vector_indexed = Column(Boolean, nullable=False, default=False, index=True)
    vector_indexed_at = Column(DateTime, nullable=True)
    graph_indexed = Column(Boolean, nullable=False, default=False, index=True)
    graph_indexed_at = Column(DateTime, nullable=True)
    entities_extracted = Column(Boolean, nullable=False, default=False, index=True)
    entities_extracted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    processing_jobs = relationship("ProcessingJob", back_populates="audio_file")
    
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
            "language": self.language,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "processing_status": self.processing_status.value if self.processing_status else None,
            "error_message": self.error_message,
            "tag": self.tag,
            "category": self.category,
            "vector_indexed": self.vector_indexed,
            "vector_indexed_at": self.vector_indexed_at.isoformat() if self.vector_indexed_at else None,
            "graph_indexed": self.graph_indexed,
            "graph_indexed_at": self.graph_indexed_at.isoformat() if self.graph_indexed_at else None,
            "entities_extracted": self.entities_extracted,
            "entities_extracted_at": self.entities_extracted_at.isoformat() if self.entities_extracted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }