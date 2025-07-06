"""
Backend integration module for data_pipeline.

This module provides a bridge between the file-watching data pipeline 
and the existing backend audio processing logic, allowing code reuse
without duplication.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add backend to Python path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Backend imports
from core.config import settings
from core.database import async_session
from models.audio_file import ProcessingStatus
from repositories.audio_repository import AudioRepository
from services.audio_storage import AudioStorageService
from services.transcription_service import TranscriptionService
from services.ollama_service import OllamaService
from models.job import JobType, ProcessingJob, JobStatus

logger = logging.getLogger(__name__)


class BackendAudioProcessor:
    """
    Audio processor that reuses backend logic for data pipeline.
    
    This class bridges the gap between file-watching pipeline and
    backend processing without code duplication.
    """
    
    def __init__(self):
        self.storage_service = AudioStorageService()
        
    async def process_audio_file_from_pipeline(
        self, 
        file_path: Path,
        user_id: str = "data_pipeline",
        language: str = "en"
    ) -> Optional[str]:
        """
        Process an audio file using backend logic but triggered from data pipeline.
        
        Args:
            file_path: Path to the audio file in source_data folder
            user_id: User identifier (defaults to "data_pipeline")
            language: Language code for transcription
            
        Returns:
            Audio file ID if successful, None if failed
        """
        try:
            # Create async database session
            async with async_session() as db:
                audio_repo = AudioRepository(db)
                
                # Step 1: Move file to backend storage structure
                stored_file_info = await self._store_file_in_backend(file_path, user_id)
                if not stored_file_info:
                    logger.error(f"Failed to store file in backend storage: {file_path}")
                    return None
                
                # Step 2: Create AudioFile record using backend model
                audio_record = await audio_repo.create({
                    "filename": stored_file_info["filename"],
                    "original_filename": stored_file_info["original_filename"], 
                    "file_path": stored_file_info["file_path"],
                    "file_size_bytes": stored_file_info["file_size_bytes"],
                    "mime_type": stored_file_info["mime_type"],
                    "user_id": user_id,
                    "language": language,
                    "upload_timestamp": datetime.utcnow(),
                    "processing_status": ProcessingStatus.UPLOADED,
                    "source": "data_pipeline"  # Mark as pipeline-sourced
                })
                
                logger.info(f"Created audio record {audio_record.id} for pipeline file {file_path}")
                
                # Step 3: Trigger Celery task for processing (like audio router)
                await self._trigger_transcription_task(audio_record.id, stored_file_info["file_path"], user_id)
                
                return str(audio_record.id)
                
        except Exception as e:
            logger.error(f"Error processing audio file {file_path}: {e}", exc_info=True)
            return None
    
    async def _trigger_transcription_task(self, audio_id, file_path: str, user_id: str):
        """Dispatch Celery task for transcription (similar to audio_router.py)."""
        from workers.tasks.transcription_tasks import transcribe_audio
        from sqlalchemy.future import select
        from models.audio_file import AudioFile
        
        try:
            async with async_session() as db:
                # Get audio file record
                result = await db.execute(select(AudioFile).filter(AudioFile.id == audio_id))
                audio_file = result.scalar_one_or_none()
                
                if not audio_file:
                    logger.error(f"Audio file {audio_id} not found, cannot start transcription job.")
                    return
                
                # Create processing job
                job = ProcessingJob(
                    job_type=JobType.TRANSCRIPTION,
                    status=JobStatus.PENDING,
                    input_data={"audio_id": str(audio_id), "file_path": file_path},
                    user_id=user_id,
                    audio_file_id=audio_id
                )
                db.add(job)
                await db.commit()
                await db.refresh(job)
                
                # Dispatch Celery task
                task_result = transcribe_audio.delay(audio_id=str(audio_id), job_id=str(job.id))
                job.celery_task_id = task_result.id
                await db.commit()
                
                logger.info(f"Dispatched transcription task {task_result.id} for audio {audio_id} from data_pipeline")
                
        except Exception as e:
            logger.error(f"Failed to dispatch transcription task for {audio_id}: {e}", exc_info=True)
    
    async def _store_file_in_backend(self, source_path: Path, user_id: str) -> Optional[dict]:
        """
        Store file using backend storage service.
        
        Args:
            source_path: Original file path in data_pipeline/source_data
            user_id: User identifier
            
        Returns:
            File info dict or None if failed
        """
        try:
            # Create a mock UploadFile object from the source file
            from fastapi import UploadFile
            import io
            
            # Read file content
            with open(source_path, 'rb') as f:
                file_content = f.read()
            
            # Create UploadFile-like object
            upload_file = UploadFile(
                filename=source_path.name,
                file=io.BytesIO(file_content),
                size=len(file_content)
            )
            
            # Use backend storage service
            file_info = await self.storage_service.save_audio_file(upload_file, user_id)
            
            # Clean up original file after successful storage
            if file_info:
                source_path.unlink()  # Delete original file
                logger.info(f"Moved {source_path} to backend storage: {file_info['file_path']}")
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error storing file {source_path}: {e}")
            return None
    
    async def get_processing_status(self, audio_id: str) -> Optional[dict]:
        """
        Get processing status using backend repository and job tracking.
        
        Args:
            audio_id: Audio file UUID
            
        Returns:
            Status information dict with job details
        """
        try:
            from uuid import UUID
            from sqlalchemy.future import select
            from repositories.job_repository import JobRepository
            
            async with async_session() as db:
                audio_repo = AudioRepository(db)
                job_repo = JobRepository(db)
                
                audio_file = await audio_repo.get_by_id(UUID(audio_id))
                if not audio_file:
                    return None
                
                # Get recent jobs for this audio file
                jobs = await job_repo.get_by_audio_file_id(UUID(audio_id))
                
                # Get latest job status
                latest_job = jobs[0] if jobs else None
                
                return {
                    "id": str(audio_file.id),
                    "filename": audio_file.original_filename,
                    "status": audio_file.processing_status,
                    "original_transcript": audio_file.original_transcript,
                    "improved_transcript": audio_file.improved_transcript,
                    "vector_indexed": audio_file.vector_indexed,
                    "graph_indexed": audio_file.graph_indexed,
                    "entities_extracted": audio_file.entities_extracted,
                    "upload_timestamp": audio_file.upload_timestamp.isoformat() if audio_file.upload_timestamp else None,
                    "latest_job": {
                        "id": str(latest_job.id),
                        "type": latest_job.job_type,
                        "status": latest_job.status,
                        "progress": latest_job.progress,
                        "error_message": latest_job.error_message,
                        "started_at": latest_job.started_at.isoformat() if latest_job.started_at else None,
                        "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None
                    } if latest_job else None
                }
                
        except Exception as e:
            logger.error(f"Error getting status for {audio_id}: {e}")
            return None
    
    async def get_job_progress(self, audio_id: str) -> Optional[dict]:
        """
        Get detailed job progress for an audio file.
        
        Args:
            audio_id: Audio file UUID
            
        Returns:
            Job progress information
        """
        try:
            from uuid import UUID
            from repositories.job_repository import JobRepository
            
            async with async_session() as db:
                job_repo = JobRepository(db)
                jobs = await job_repo.get_by_audio_file_id(UUID(audio_id))
                
                if not jobs:
                    return None
                
                # Get all jobs for this audio file
                job_info = []
                for job in jobs:
                    job_info.append({
                        "id": str(job.id),
                        "type": job.job_type,
                        "status": job.status,
                        "progress": job.progress,
                        "error_message": job.error_message,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "celery_task_id": job.celery_task_id
                    })
                
                return {
                    "audio_id": audio_id,
                    "total_jobs": len(jobs),
                    "completed_jobs": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
                    "failed_jobs": len([j for j in jobs if j.status == JobStatus.FAILED]),
                    "jobs": job_info
                }
                
        except Exception as e:
            logger.error(f"Error getting job progress for {audio_id}: {e}")
            return None


class FileWatcherCallback:
    """
    Callback handler for file watcher that uses backend processing.
    """
    
    def __init__(self):
        self.processor = BackendAudioProcessor()
        
    def __call__(self, file_path: Path):
        """
        Process new file detected by watcher.
        
        Args:
            file_path: Path to the new file
        """
        # Run async processing in event loop
        asyncio.run(self._process_file_async(file_path))
    
    async def _process_file_async(self, file_path: Path):
        """
        Async wrapper for file processing.
        
        Args:
            file_path: Path to the new file
        """
        # Check if file is audio
        if file_path.suffix.lower() in {'.mp3', '.m4a', '.wav', '.ogg', '.webm', '.aac', '.flac'}:
            logger.info(f"Processing audio file: {file_path}")
            
            # Extract language from filename if present (e.g., file_en.mp3, file_fr.mp3)
            language = "en"  # default
            stem = file_path.stem
            if "_" in stem:
                parts = stem.split("_")
                last_part = parts[-1].lower()
                if last_part in ["en", "fr", "es", "de", "it"]:  # Add more as needed
                    language = last_part
            
            # Process using backend logic
            audio_id = await self.processor.process_audio_file_from_pipeline(
                file_path, 
                user_id="data_pipeline",
                language=language
            )
            
            if audio_id:
                logger.info(f"Successfully processed {file_path} as audio {audio_id}")
                
                # Optional: Send enhanced webhook notification 
                try:
                    from notifier import send_webhook
                    
                    # Get initial status with job info
                    status_info = await self.processor.get_processing_status(audio_id)
                    
                    send_webhook({
                        "audio_id": audio_id,
                        "filename": file_path.name,
                        "status": "processing_started",
                        "source": "data_pipeline",
                        "job_info": status_info.get("latest_job") if status_info else None,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Failed to send webhook for {file_path}: {e}")
            else:
                logger.error(f"Failed to process audio file: {file_path}")
        else:
            logger.info(f"Skipping non-audio file: {file_path}")


def create_pipeline_callback():
    """
    Create a callback function for the file watcher that uses backend processing.
    
    Returns:
        Callable that can be used with the existing watcher
    """
    return FileWatcherCallback()


# Compatibility function for existing pipeline.py
def process_file_with_backend(file_path: Path):
    """
    Drop-in replacement for the original process_file function.
    Uses backend logic instead of pipeline-specific processing.
    
    Args:
        file_path: Path to the file to process
    """
    callback = FileWatcherCallback()
    callback(file_path)


if __name__ == "__main__":
    # Test the integration
    import tempfile
    
    async def test_integration():
        processor = BackendAudioProcessor()
        
        # Create a dummy audio file for testing
        test_file = Path("test_audio.mp3")
        if test_file.exists():
            audio_id = await processor.process_audio_file_from_pipeline(test_file)
            if audio_id:
                status = await processor.get_processing_status(audio_id)
                print(f"Processing status: {status}")
            else:
                print("Processing failed")
        else:
            print("No test file found")
    
    asyncio.run(test_integration())