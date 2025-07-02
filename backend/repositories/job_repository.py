"""Repository for job management operations."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func

from models.job import ProcessingJob, JobStatusHistory, JobStatus, JobType
from core.database import get_db_session

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for managing processing jobs."""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or next(get_db_session())
    
    def create_job(
        self,
        job_type: JobType,
        input_data: Dict[str, Any] = None,
        user_id: str = None,
        audio_file_id: UUID = None,
        priority: int = 0,
        max_retries: int = 3,
        timeout_seconds: int = None
    ) -> ProcessingJob:
        """Create a new processing job."""
        job = ProcessingJob(
            job_type=job_type,
            status=JobStatus.PENDING,
            input_data=input_data,
            user_id=user_id,
            audio_file_id=audio_file_id,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Add initial status history
        self.add_status_history(job.id, None, JobStatus.PENDING, "Job created")
        
        logger.info(f"Created job {job.id} of type {job_type}")
        return job
    
    def get_job(self, job_id: UUID, include_history: bool = False) -> Optional[ProcessingJob]:
        """Get a job by ID."""
        query = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id)
        
        if include_history:
            query = query.options(joinedload(ProcessingJob.status_history))
        
        return query.first()
    
    def get_jobs_by_status(
        self, 
        status: JobStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[ProcessingJob]:
        """Get jobs by status."""
        return (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status == status)
            .order_by(desc(ProcessingJob.priority), ProcessingJob.created_at)
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_jobs_by_type(
        self,
        job_type: JobType,
        status: JobStatus = None,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """Get jobs by type and optionally status."""
        query = self.db.query(ProcessingJob).filter(ProcessingJob.job_type == job_type)
        
        if status:
            query = query.filter(ProcessingJob.status == status)
        
        return (
            query.order_by(desc(ProcessingJob.created_at))
            .limit(limit)
            .all()
        )
    
    def get_jobs_by_user(
        self,
        user_id: str,
        status: JobStatus = None,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """Get jobs for a specific user."""
        query = self.db.query(ProcessingJob).filter(ProcessingJob.user_id == user_id)
        
        if status:
            query = query.filter(ProcessingJob.status == status)
        
        return (
            query.order_by(desc(ProcessingJob.created_at))
            .limit(limit)
            .all()
        )
    
    def get_jobs_by_audio_id(
        self,
        audio_file_id: UUID,
        status: str = None,
        limit: int = 100
    ) -> List[ProcessingJob]:
        """Get jobs for a specific audio file."""
        query = self.db.query(ProcessingJob).filter(ProcessingJob.audio_file_id == audio_file_id)
        
        if status:
            # Handle both string and JobStatus enum
            if isinstance(status, str):
                try:
                    status_enum = JobStatus(status)
                    query = query.filter(ProcessingJob.status == status_enum)
                except ValueError:
                    # If invalid status string, return empty list
                    return []
            else:
                query = query.filter(ProcessingJob.status == status)
        
        return (
            query.order_by(desc(ProcessingJob.created_at))
            .limit(limit)
            .all()
        )
    
    def get_pending_jobs(self, limit: int = 100) -> List[ProcessingJob]:
        """Get pending jobs ordered by priority."""
        return (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.status == JobStatus.PENDING)
            .order_by(desc(ProcessingJob.priority), ProcessingJob.created_at)
            .limit(limit)
            .all()
        )
    
    def get_failed_jobs_for_retry(self, limit: int = 100) -> List[ProcessingJob]:
        """Get failed jobs that can be retried."""
        return (
            self.db.query(ProcessingJob)
            .filter(
                and_(
                    ProcessingJob.status == JobStatus.FAILED,
                    ProcessingJob.retry_count < ProcessingJob.max_retries
                )
            )
            .order_by(desc(ProcessingJob.priority), ProcessingJob.created_at)
            .limit(limit)
            .all()
        )
    
    def update_job_status(
        self,
        job_id: UUID,
        new_status: JobStatus,
        message: str = None,
        error_message: str = None,
        error_traceback: str = None,
        result_data: Dict[str, Any] = None,
        celery_task_id: str = None
    ) -> bool:
        """Update job status and add history entry."""
        job = self.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        old_status = job.status
        job.status = new_status
        job.updated_at = datetime.utcnow()
        
        # Update timestamps based on status
        if new_status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.completed_at = datetime.utcnow()
        
        # Update other fields
        if error_message:
            job.error_message = error_message
        if error_traceback:
            job.error_traceback = error_traceback
        if result_data:
            job.result_data = result_data
        if celery_task_id:
            job.celery_task_id = celery_task_id
        
        # Increment retry count for retrying status
        if new_status == JobStatus.RETRYING:
            job.retry_count += 1
        
        self.db.commit()
        
        # Add status history
        self.add_status_history(job_id, old_status, new_status, message)
        
        logger.info(f"Updated job {job_id} status: {old_status} -> {new_status}")
        return True
    
    def add_status_history(
        self,
        job_id: UUID,
        old_status: JobStatus = None,
        new_status: JobStatus = None,
        message: str = None,
        status_metadata: Dict[str, Any] = None
    ) -> JobStatusHistory:
        """Add a status history entry."""
        history = JobStatusHistory(
            job_id=job_id,
            old_status=old_status,
            new_status=new_status,
            message=message,
            status_metadata=status_metadata
        )
        
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        
        return history
    
    def get_job_statistics(
        self,
        since: datetime = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Get job statistics."""
        query = self.db.query(ProcessingJob)
        
        if since:
            query = query.filter(ProcessingJob.created_at >= since)
        
        if user_id:
            query = query.filter(ProcessingJob.user_id == user_id)
        
        # Count by status
        status_counts = {}
        for status in JobStatus:
            count = query.filter(ProcessingJob.status == status).count()
            status_counts[status.value] = count
        
        # Count by type
        type_counts = {}
        for job_type in JobType:
            count = query.filter(ProcessingJob.job_type == job_type).count()
            type_counts[job_type.value] = count
        
        # Calculate average duration for completed jobs
        completed_jobs = query.filter(
            and_(
                ProcessingJob.status == JobStatus.COMPLETED,
                ProcessingJob.started_at.isnot(None),
                ProcessingJob.completed_at.isnot(None)
            )
        ).all()
        
        avg_duration = None
        if completed_jobs:
            durations = [job.duration_seconds for job in completed_jobs if job.duration_seconds]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "total_jobs": query.count(),
            "status_counts": status_counts,
            "type_counts": type_counts,
            "average_duration_seconds": avg_duration,
            "period_start": since.isoformat() if since else None,
            "user_id": user_id
        }
    
    def cleanup_old_jobs(
        self,
        days_old: int = 30,
        keep_failed: bool = True
    ) -> int:
        """Clean up old completed jobs."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        query = self.db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.created_at < cutoff_date,
                ProcessingJob.status == JobStatus.COMPLETED
            )
        )
        
        if keep_failed:
            # Only delete completed jobs, keep failed ones for analysis
            query = query.filter(ProcessingJob.status == JobStatus.COMPLETED)
        else:
            # Delete both completed and failed jobs
            query = query.filter(
                ProcessingJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
            )
        
        count = query.count()
        query.delete(synchronize_session=False)
        self.db.commit()
        
        logger.info(f"Cleaned up {count} old jobs older than {days_old} days")
        return count
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        pending_count = self.db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.PENDING
        ).count()
        
        processing_count = self.db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.PROCESSING
        ).count()
        
        failed_count = self.db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.FAILED
        ).count()
        
        retry_eligible = self.db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.status == JobStatus.FAILED,
                ProcessingJob.retry_count < ProcessingJob.max_retries
            )
        ).count()
        
        return {
            "pending": pending_count,
            "processing": processing_count,
            "failed": failed_count,
            "retry_eligible": retry_eligible,
            "total_active": pending_count + processing_count
        }