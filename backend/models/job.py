"""Job queue database models."""
import uuid
import enum
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, enum.Enum):
    """Job type enumeration."""
    TRANSCRIPT_PROCESSING = "transcript_processing"
    VECTOR_INDEXING = "vector_indexing"
    GRAPH_BUILDING = "graph_building"
    DOCUMENT_CHUNKING = "document_chunking"
    ENTITY_EXTRACTION = "entity_extraction"
    PLUGIN_EXECUTION = "plugin_execution"


class ProcessingJob(Base):
    """Processing job database model."""
    
    __tablename__ = "processing_jobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Job configuration
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    priority = Column(Integer, nullable=False, default=0)
    
    # Job data
    input_data = Column(JSONB, nullable=True)
    result_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # References
    user_id = Column(String(255), nullable=True, index=True)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey('audio_files.id', ondelete='SET NULL'), nullable=True, index=True)
    celery_task_id = Column(String(255), nullable=True, index=True)
    
    # Retry configuration
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audio_file = relationship("AudioFile", back_populates="processing_jobs")
    status_history = relationship("JobStatusHistory", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, type={self.job_type}, status={self.status})>"
    
    @property
    def is_finished(self) -> bool:
        """Check if job is in a finished state."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED]
    
    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in [JobStatus.PROCESSING, JobStatus.RETRYING]
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED and 
            self.retry_count < self.max_retries
        )
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": str(self.id),
            "job_type": self.job_type.value,
            "status": self.status.value,
            "priority": self.priority,
            "input_data": self.input_data,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "user_id": self.user_id,
            "audio_file_id": str(self.audio_file_id) if self.audio_file_id else None,
            "celery_task_id": self.celery_task_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_finished": self.is_finished,
            "is_active": self.is_active,
            "can_retry": self.can_retry,
            "duration_seconds": self.duration_seconds
        }


class JobStatusHistory(Base):
    """Job status change history."""
    
    __tablename__ = "job_status_history"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to job
    job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Status change
    old_status = Column(SQLEnum(JobStatus), nullable=True)
    new_status = Column(SQLEnum(JobStatus), nullable=False)
    message = Column(Text, nullable=True)
    status_metadata = Column(JSONB, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationship
    job = relationship("ProcessingJob", back_populates="status_history")
    
    def __repr__(self):
        return f"<JobStatusHistory(job_id={self.job_id}, {self.old_status} -> {self.new_status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status history to dictionary."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "old_status": self.old_status.value if self.old_status else None,
            "new_status": self.new_status.value,
            "message": self.message,
            "status_metadata": self.status_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }