"""Celery task for audio transcription."""
import logging
import asyncio
from uuid import UUID

from workers.celery_app import app
from workers.base_task import BaseTask
from models.audio_file import ProcessingStatus
from core.config import settings
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

@app.task(base=BaseTask, bind=True)
def transcribe_audio(self, audio_id: str, job_id: str = None):
    """Transcribes an audio file and triggers the next processing step."""
    
    async def _transcribe_async():
        from core.database import async_session
        from repositories.audio_repository import AudioRepository
        from services.transcription_service import TranscriptionService

        self._job_id = UUID(job_id) if job_id else None
        audio_uuid = UUID(audio_id)

        async with async_session() as db:
            audio_repo = AudioRepository(db)
            try:
                self.log_progress(1, 3, "Starting transcription")
                await audio_repo.update_status(audio_uuid, ProcessingStatus.TRANSCRIBING)

                audio_file = await audio_repo.get_by_id(audio_uuid)
                if not audio_file:
                    raise ValueError(f"Audio file {audio_id} not found")

                transcription_service = TranscriptionService()
                transcription_result = await transcription_service.transcribe_audio(
                    audio_file.file_path,
                    settings.transcription_engine,
                    language=audio_file.language or 'en'
                )

                if not transcription_result["success"]:
                    raise RuntimeError(f"Transcription failed: {transcription_result.get('error')}")

                await audio_repo.update(audio_uuid, {
                    "original_transcript": transcription_result["transcript"],
                    "transcription_engine": transcription_result["engine"],
                    "duration_seconds": await transcription_service.get_audio_duration(audio_file.file_path)
                })
                
                self.log_progress(2, 3, "Original transcription complete, awaiting transcript improvement")
                await audio_repo.update_status(audio_uuid, ProcessingStatus.IMPROVING)

                ollama_service = OllamaService()
                
                improvement_result = await ollama_service.improve_transcript(
                    audio_file.original_transcript,
                    language=audio_file.language or 'en'
                )
                
                if improvement_result["success"]:
                    await audio_repo.update(audio_uuid, {"improved_transcript": improvement_result["improved_transcript"]})
                else:
                    logger.warning(f"Transcript improvement failed for {audio_id}, using original.")
                    await audio_repo.update(audio_uuid, {"improved_transcript": audio_file.original_transcript})

                # Do NOT chain to process_transcript - wait for user confirmation
                
                self.log_progress(2, 3, "Transcription complete, awaiting user review")
                await audio_repo.update_status(audio_uuid, ProcessingStatus.PENDING_REVIEW)

                return {"status": "success", "audio_id": audio_id}

            except Exception as e:
                logger.error(f"Transcription task failed for audio {audio_id}: {e}", exc_info=True)
                await audio_repo.update_status(audio_uuid, ProcessingStatus.FAILED, str(e))
                raise

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_transcribe_async())
