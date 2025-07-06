"""Audio file upload and management API routes."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from models.audio_file import ProcessingStatus
from repositories.audio_repository import AudioRepository
from services.audio_storage import AudioStorageService
from schemas.audio import (
    AudioFileResponse,
    AudioFileListResponse,
    AudioUploadResponse,
    AudioTagUpdateRequest,
    AudioTagsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".webm", ".aac", ".flac"}
ALLOWED_MIME_TYPES = {
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/webm",
    "audio/aac",
    "audio/x-m4a",
    "audio/flac",
    "application/octet-stream"  # Fallback for when MIME type detection fails
}


@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
    db: AsyncSession = Depends(get_db)
):
    """Upload an audio file for transcription and processing.
    
    Args:
        file: The audio file to upload
        user_id: Optional user identifier
        language: Language code for transcription (e.g., 'en', 'fr')
        
    Returns:
        AudioUploadResponse with file ID and status
    """
    # Validate file extension
    file_extension = file.filename.lower().split(".")[-1] if file.filename else ""
    if f".{file_extension}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate MIME type (more lenient - prioritize file extension)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        # If MIME type is not recognized but file extension is valid, log a warning but continue
        if file.content_type == "application/octet-stream":
            logger.warning(f"Generic MIME type received for file {file.filename}, using extension validation")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MIME type '{file.content_type}'. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )
    
    try:
        # Initialize services
        storage_service = AudioStorageService()
        audio_repo = AudioRepository(db)
        
        # Save file to storage
        file_info = await storage_service.save_audio_file(file, user_id)
        
        # Create database record
        audio_record = await audio_repo.create({
            "filename": file_info["filename"],
            "original_filename": file_info["original_filename"],
            "file_path": file_info["file_path"],
            "file_size_bytes": file_info["file_size_bytes"],
            "mime_type": file_info["mime_type"],
            "user_id": user_id,
            "language": language or "en",
            "upload_timestamp": datetime.utcnow(),
            "processing_status": ProcessingStatus.UPLOADED
        })
        
        # Add background task for processing
        background_tasks.add_task(
            trigger_transcription_task,
            audio_id=audio_record.id,
            file_path=file_info["file_path"]
        )
        
        logger.info(f"Audio file uploaded successfully: {audio_record.id}")
        
        return AudioUploadResponse(
            id=audio_record.id,
            filename=audio_record.filename,
            original_filename=audio_record.original_filename,
            file_size_bytes=audio_record.file_size_bytes,
            upload_timestamp=audio_record.upload_timestamp,
            processing_status=audio_record.processing_status,
            message="File uploaded successfully. Processing will begin shortly."
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.get("/tags", response_model=AudioTagsResponse)
async def get_available_tags(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get list of available tags and categories.
    
    Args:
        user_id: Optional user ID filter
        
    Returns:
        AudioTagsResponse with available tags and categories
    """
    audio_repo = AudioRepository(db)
    
    # Get available tags and categories
    tags = await audio_repo.get_available_tags(user_id)
    categories = await audio_repo.get_available_categories(user_id)
    
    return AudioTagsResponse(
        tags=sorted(tags),
        categories=sorted(categories)
    )


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio_file(
    audio_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get audio file details by ID.
    
    Args:
        audio_id: UUID of the audio file
        
    Returns:
        AudioFileResponse with file details
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return AudioFileResponse.from_orm(audio_file)


@router.get("/", response_model=AudioFileListResponse)
async def list_audio_files(
    user_id: Optional[str] = None,
    status: Optional[ProcessingStatus] = None,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List audio files with optional filters.
    
    Args:
        user_id: Filter by user ID
        status: Filter by processing status
        tag: Filter by tag
        category: Filter by category
        limit: Maximum number of results (default 20)
        offset: Number of results to skip (default 0)
        
    Returns:
        AudioFileListResponse with paginated results
    """
    audio_repo = AudioRepository(db)
    
    # Get filtered results
    audio_files, total_count = await audio_repo.list_with_filters(
        user_id=user_id,
        status=status,
        tag=tag,
        category=category,
        limit=limit,
        offset=offset
    )
    
    return AudioFileListResponse(
        items=[AudioFileResponse.from_orm(af) for af in audio_files],
        total=total_count,
        limit=limit,
        offset=offset
    )


@router.delete("/{audio_id}")
async def delete_audio_file(
    audio_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an audio file and its associated data.
    
    Args:
        audio_id: UUID of the audio file to delete
        
    Returns:
        Success message
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Delete file from storage
    storage_service = AudioStorageService()
    file_deleted = await storage_service.delete_file(audio_file.file_path)
    
    # Delete database record
    await audio_repo.delete(audio_id)
    
    logger.info(f"Audio file deleted: {audio_id}")
    
    return {
        "message": "Audio file deleted successfully",
        "file_deleted": file_deleted
    }


@router.get("/{audio_id}/download")
async def download_audio_file(
    audio_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download the original audio file.
    
    Args:
        audio_id: UUID of the audio file
        
    Returns:
        FileResponse with the audio file
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    storage_service = AudioStorageService()
    file_path = storage_service.get_file_path(
        audio_file.filename,
        audio_file.upload_timestamp.strftime("%Y/%m/%d") if audio_file.upload_timestamp else None
    )
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found in storage")
    
    return FileResponse(
        path=str(file_path),
        filename=audio_file.original_filename or audio_file.filename,
        media_type=audio_file.mime_type or "audio/mpeg"
    )


@router.get("/{audio_id}/transcript")
async def get_transcript(
    audio_id: UUID,
    improved: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get the transcript for an audio file.
    
    Args:
        audio_id: UUID of the audio file
        improved: Whether to return improved transcript (default True)
        
    Returns:
        Transcript text or status message
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Check processing status
    if audio_file.processing_status in [ProcessingStatus.UPLOADED, ProcessingStatus.TRANSCRIBING]:
        return {
            "status": audio_file.processing_status,
            "message": "Transcription in progress"
        }
    
    if audio_file.processing_status == ProcessingStatus.FAILED:
        return {
            "status": audio_file.processing_status,
            "message": "Transcription failed",
            "error": audio_file.error_message
        }
    
    # Return transcript
    transcript = (
        audio_file.improved_transcript if improved and audio_file.improved_transcript
        else audio_file.original_transcript
    )
    
    if not transcript:
        return {
            "status": audio_file.processing_status,
            "message": "No transcript available"
        }
    
    return {
        "status": audio_file.processing_status,
        "transcript": transcript,
        "is_improved": bool(improved and audio_file.improved_transcript),
        "transcription_engine": audio_file.transcription_engine
    }


async def trigger_transcription_task(audio_id: UUID, file_path: str):
    """Dispatches a Celery task to transcribe the audio file."""
    from workers.tasks.transcription_tasks import transcribe_audio
    from models.job import JobType, ProcessingJob, JobStatus
    from core.database import async_session
    from models.audio_file import AudioFile
    from sqlalchemy.future import select

    logger.info(f"Dispatching transcription task for audio {audio_id}")

    async with async_session() as db:
        try:
            result = await db.execute(select(AudioFile).filter(AudioFile.id == audio_id))
            audio_file = result.scalar_one_or_none()

            if not audio_file:
                logger.error(f"Audio file {audio_id} not found, cannot start transcription job.")
                return

            job = ProcessingJob(
                job_type=JobType.TRANSCRIPTION,
                status=JobStatus.PENDING,
                input_data={"audio_id": str(audio_id), "file_path": file_path},
                user_id=audio_file.user_id,
                audio_file_id=audio_id
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            task_result = transcribe_audio.delay(audio_id=str(audio_id), job_id=str(job.id))
            job.celery_task_id = task_result.id
            await db.commit()

            logger.info(f"Dispatched transcription task {task_result.id} for audio {audio_id}")

        except Exception as e:
            logger.error(f"Failed to dispatch transcription task for {audio_id}: {e}", exc_info=True)


@router.get("/{audio_id}/indexing-status")
async def get_indexing_status(
    audio_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the brain indexing status for an audio file.
    
    Args:
        audio_id: UUID of the audio file
        
    Returns:
        Indexing status including vector, graph, and entity extraction status
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Check if there's an active job for this audio file
    from models.job import JobType, JobStatus, ProcessingJob
    from sqlalchemy import select, and_
    
    # Query for active job directly using async session
    result = await db.execute(
        select(ProcessingJob).where(
            and_(
                ProcessingJob.audio_file_id == audio_id,
                ProcessingJob.job_type == JobType.TRANSCRIPT_PROCESSING,
                ProcessingJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING])
            )
        ).order_by(ProcessingJob.created_at.desc())
    )
    active_job = result.scalar_one_or_none()
    
    return {
        "audio_id": str(audio_id),
        "processing_status": audio_file.processing_status,
        "indexing": {
            "vector_indexed": audio_file.vector_indexed,
            "vector_indexed_at": audio_file.vector_indexed_at.isoformat() if audio_file.vector_indexed_at else None,
            "graph_indexed": audio_file.graph_indexed,
            "graph_indexed_at": audio_file.graph_indexed_at.isoformat() if audio_file.graph_indexed_at else None,
            "entities_extracted": audio_file.entities_extracted,
            "entities_extracted_at": audio_file.entities_extracted_at.isoformat() if audio_file.entities_extracted_at else None
        },
        "active_job": {
            "id": str(active_job.id),
            "status": active_job.status,
            "progress": active_job.progress,
            "current_step": active_job.current_step,
            "total_steps": active_job.total_steps,
            "created_at": active_job.created_at.isoformat()
        } if active_job else None
    }


@router.put("/{audio_id}/tags", response_model=AudioFileResponse)
async def update_audio_tags(
    audio_id: UUID,
    tag_update: AudioTagUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update tags and categories for an audio file.
    
    Args:
        audio_id: UUID of the audio file
        tag_update: Tag and category updates
        
    Returns:
        Updated AudioFileResponse
    """
    audio_repo = AudioRepository(db)
    audio_file = await audio_repo.get_by_id(audio_id)
    
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Update tags/categories
    update_data = {}
    if tag_update.tag is not None:
        update_data["tag"] = tag_update.tag.strip() if tag_update.tag.strip() else None
    if tag_update.category is not None:
        update_data["category"] = tag_update.category.strip() if tag_update.category.strip() else None
    
    if update_data:
        updated_file = await audio_repo.update(audio_id, update_data)
        if updated_file:
            logger.info(f"Updated tags for audio file {audio_id}: {update_data}")
            return AudioFileResponse.from_orm(updated_file)
    
    return AudioFileResponse.from_orm(audio_file)