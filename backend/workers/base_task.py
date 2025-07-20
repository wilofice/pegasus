"""Base task class for all Celery tasks."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from celery import Task
from celery.exceptions import Retry, Ignore

from core.database import get_db_session
from models.job import JobStatus
from repositories.job_repository import JobRepository
from services.neo4j_client import get_neo4j_client, close_neo4j_client
from services.qdrant_db_client import get_qdrant_client, close_qdrant_client
from services.neo4j_document_ingestion import Neo4jDocumentIngestion

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """Base task class with database connections and error handling."""
    
    def __init__(self):
        self.db_session = None
        self.job_repo = None
        self.neo4j_client = None
        self.qdrant_client = None
        self.neo4j_ingestion = None
        self._job_id = None
    
    def before_start(self, task_id, args, kwargs):
        """Initialize resources before task execution."""
        try:
            # Set up database session
            self.db_session = next(get_db_session())
            self.job_repo = JobRepository(self.db_session)
            
            # Initialize database clients
            self.neo4j_client = get_neo4j_client()
            self.qdrant_client = get_qdrant_client()
            self.neo4j_ingestion = Neo4jDocumentIngestion()
            
            # Extract job_id if provided
            if 'job_id' in kwargs:
                self._job_id = kwargs['job_id']
                self.update_job_status(JobStatus.PROCESSING, f"Task {task_id} started")
            
            logger.info(f"Task {task_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize task {task_id}: {e}")
            if self._job_id:
                self.update_job_status(
                    JobStatus.FAILED, 
                    f"Initialization failed: {str(e)}"
                )
            raise
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up resources after task completion."""
        try:
            # Update job status based on task result
            if self._job_id:
                if status == 'SUCCESS':
                    self.update_job_status(
                        JobStatus.COMPLETED,
                        "Task completed successfully",
                        result_data=retval if isinstance(retval, dict) else {"result": retval}
                    )
                elif status == 'RETRY':
                    self.update_job_status(
                        JobStatus.RETRYING,
                        f"Task retrying: {str(einfo)}"
                    )
            
            # Close database connections
            if self.db_session:
                self.db_session.close()
            
            # Note: Neo4j and ChromaDB connections are managed globally
            # and don't need to be closed per task
            
            logger.info(f"Task {task_id} cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during task cleanup {task_id}: {e}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        try:
            error_message = str(exc)
            error_traceback = str(einfo)
            
            logger.error(f"Task {task_id} failed: {error_message}")
            
            if self._job_id:
                self.update_job_status(
                    JobStatus.FAILED,
                    f"Task failed: {error_message}",
                    error_message=error_message,
                    error_traceback=error_traceback
                )
        
        except Exception as e:
            logger.error(f"Error handling task failure {task_id}: {e}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        try:
            retry_message = f"Task retrying due to: {str(exc)}"
            logger.warning(f"Task {task_id} retrying: {retry_message}")
            
            if self._job_id:
                self.update_job_status(
                    JobStatus.RETRYING,
                    retry_message
                )
        
        except Exception as e:
            logger.error(f"Error handling task retry {task_id}: {e}")
    
    def update_job_status(
        self,
        status: JobStatus,
        message: str = None,
        error_message: str = None,
        error_traceback: str = None,
        result_data: Dict[str, Any] = None
    ) -> bool:
        """Update job status in database."""
        if not self._job_id or not self.job_repo:
            return False
        
        try:
            return self.job_repo.update_job_status(
                job_id=self._job_id,
                new_status=status,
                message=message,
                error_message=error_message,
                error_traceback=error_traceback,
                result_data=result_data,
                celery_task_id=self.request.id
            )
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            return False
    
    def get_job_input_data(self) -> Optional[Dict[str, Any]]:
        """Get input data from the associated job."""
        if not self._job_id or not self.job_repo:
            return None
        
        try:
            job = self.job_repo.get_job(self._job_id)
            return job.input_data if job else None
        except Exception as e:
            logger.error(f"Failed to get job input data: {e}")
            return None
    
    def log_progress(self, current: int, total: int, message: str = None):
        """Log task progress."""
        percentage = (current / total) * 100 if total > 0 else 0
        log_message = f"Progress: {current}/{total} ({percentage:.1f}%)"
        if message:
            log_message += f" - {message}"
        
        logger.info(log_message)
        
        # Update task state with progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percentage': percentage,
                'message': message
            }
        )
    
    def validate_input(self, required_fields: list, input_data: dict) -> bool:
        """Validate required input fields."""
        missing_fields = []
        
        for field in required_fields:
            if field not in input_data or input_data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            error_msg = f"Missing required fields: {missing_fields}"
            logger.error(error_msg)
            if self._job_id:
                self.update_job_status(JobStatus.FAILED, error_msg)
            raise ValueError(error_msg)
        
        return True
    
    def safe_execute(self, func, *args, **kwargs):
        """Execute a function with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    def should_retry(self, exc: Exception, max_retries: int = 3) -> bool:
        """Determine if task should be retried based on exception type."""
        # Retry on connection errors and temporary failures
        retry_exceptions = (
            ConnectionError,
            TimeoutError,
            # Add other retryable exceptions as needed
        )
        
        if isinstance(exc, retry_exceptions):
            if self.request.retries < max_retries:
                return True
        
        return False