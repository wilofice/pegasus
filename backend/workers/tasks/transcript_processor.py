"""Transcript processing tasks."""
import logging
import asyncio
from typing import Any, Dict
from uuid import UUID
from datetime import datetime

from workers.celery_app import app
from workers.base_task import BaseTask
from models.job import JobType, JobStatus
from models.audio_file import ProcessingStatus
from core.config import settings

logger = logging.getLogger(__name__)


@app.task(base=BaseTask, bind=True)
def process_transcript(self, audio_id: str, job_id: str = None):
    """Process audio transcript through the full brain pipeline."""
    
    async def _process_transcript_async():
        from core.database import async_session
        from repositories.audio_repository import AudioRepository

        self._job_id = UUID(job_id) if job_id else None
        audio_uuid = UUID(audio_id)

        async with async_session() as db:
            audio_repo = AudioRepository(db)
            try:
                self.log_progress(1, 7, "Improving transcript")
                await audio_repo.update_status(audio_uuid, ProcessingStatus.IMPROVING)
                
                audio_file = await audio_repo.get_by_id(audio_uuid)
                if not audio_file or not audio_file.original_transcript:
                    raise ValueError(f"Audio file {audio_id} or its transcript not found")

                from services.ollama_service import OllamaService
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

                audio_file = await audio_repo.get_by_id(audio_uuid)
                
                self.log_progress(2, 7, "Chunking transcript")
                from services.chunking_service import ChunkingService
                chunker = ChunkingService()
                chunks = chunker.chunk_text(audio_file.improved_transcript)
                
                self.log_progress(3, 7, "Analyzing sentiment")
                from services.sentiment_service import SentimentService
                sentiment_service = SentimentService()
                
                self.log_progress(4, 7, "Extracting entities")
                from services.ner_service import NERService
                ner_service = NERService()

                all_entities = []
                chunk_metadatas = []
                for i, chunk in enumerate(chunks):
                    entities = ner_service.extract_entities(chunk.text, language=audio_file.language or 'en')
                    all_entities.extend(entities)
                    sentiment = sentiment_service.analyze_sentiment(chunk.text)
                    
                    metadata = {
                        "audio_id": str(audio_id), "user_id": str(audio_file.user_id) if audio_file.user_id else "",
                        "chunk_index": i, "chunk_total": len(chunks),
                        "timestamp": audio_file.upload_timestamp.isoformat() if audio_file.upload_timestamp else "",
                        "language": audio_file.language or "en", "tags": str(audio_file.tag) if audio_file.tag else "",
                        "category": str(audio_file.category) if audio_file.category else "",
                        "entity_count": len(entities), "start_pos": int(chunk.start) if chunk.start is not None else 0,
                        "end_pos": int(chunk.end) if chunk.end is not None else 0,
                        "sentiment_score": sentiment["score"], "sentiment_classification": sentiment["classification"]
                    }
                    chunk_metadatas.append(metadata)

                self.log_progress(5, 7, "Storing chunks in ChromaDB")
                await self.chromadb_client.add_documents(
                    documents=[c.text for c in chunks],
                    metadatas=chunk_metadatas,
                    ids=[f"{audio_id}_chunk_{i}" for i in range(len(chunks))]
                )
                
                self.log_progress(6, 7, "Creating graph nodes in Neo4j")
                from services.graph_builder import GraphBuilder
                graph_builder = GraphBuilder(self.neo4j_client)
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{audio_id}_chunk_{i}"
                    chunk_entities = [e for e in all_entities if chunk.start <= e.get('start', 0) < chunk.end]
                    await graph_builder.create_chunk_node(
                        chunk_id=chunk_id, audio_id=audio_id, text=chunk.text,
                        metadata=chunk_metadatas[i], entities=chunk_entities
                    )
                
                self.log_progress(7, 7, "Finalizing processing")
                await audio_repo.update(audio_uuid, {
                    "vector_indexed": True, "vector_indexed_at": datetime.utcnow(),
                    "graph_indexed": True, "graph_indexed_at": datetime.utcnow(),
                    "entities_extracted": True, "entities_extracted_at": datetime.utcnow(),
                    "processing_status": ProcessingStatus.COMPLETED
                })
                
                result = {
                    "audio_id": audio_id, "chunks_created": len(chunks), "entities_extracted": len(all_entities),
                    "vector_indexed": True, "graph_indexed": True, "processing_completed_at": datetime.utcnow().isoformat()
                }
                logger.info(f"Successfully processed transcript for audio {audio_id}")
                return result

            except Exception as e:
                logger.error(f"Failed to process transcript for audio {audio_id}: {e}", exc_info=True)
                await audio_repo.update_status(audio_uuid, ProcessingStatus.FAILED, str(e))
                raise

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_process_transcript_async())


@app.task(base=BaseTask, bind=True)
def reprocess_transcript(self, audio_id: str, job_id: str = None):
    """Reprocess an existing transcript (e.g., after algorithm improvements)."""
    import asyncio
    
    async def _reprocess_transcript_async():
        from core.database import async_session
        from repositories.audio_repository import AudioRepository

        self._job_id = UUID(job_id) if job_id else None
        
        async with async_session() as db:
            audio_repo = AudioRepository(db)
            try:
                logger.info(f"Starting transcript reprocessing for audio {audio_id}")
                
                self.log_progress(1, 3, "Cleaning up existing data")
                
                await self.chromadb_client.delete_documents(where={"audio_id": audio_id})
                await self.neo4j_client.execute_write_query(
                    "MATCH (c:AudioChunk {audio_id: $audio_id}) DETACH DELETE c",
                    {"audio_id": audio_id}
                )
                
                await audio_repo.update(UUID(audio_id), {
                    "vector_indexed": False, "vector_indexed_at": None,
                    "graph_indexed": False, "graph_indexed_at": None,
                    "entities_extracted": False, "entities_extracted_at": None,
                    "processing_status": ProcessingStatus.PENDING_PROCESSING
                })
                
                self.log_progress(2, 3, "Reprocessing transcript")
                result = process_transcript.apply_async(
                    args=[audio_id],
                    kwargs={"job_id": job_id}
                ).get()
                
                self.log_progress(3, 3, "Reprocessing completed")
                
                return {
                    "audio_id": audio_id,
                    "reprocessed": True,
                    **result
                }
                
            except Exception as e:
                logger.error(f"Failed to reprocess transcript for audio {audio_id}: {e}", exc_info=True)
                await audio_repo.update_status(UUID(audio_id), ProcessingStatus.FAILED, f"Reprocessing failed: {e}")
                raise
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_reprocess_transcript_async())
