"""Transcript processing tasks."""
import logging
from typing import Any, Dict
from uuid import UUID

from workers.celery_app import app
from workers.base_task import BaseTask
from models.job import JobType

logger = logging.getLogger(__name__)


@app.task(base=BaseTask, bind=True)
def process_transcript(self, audio_id: str, job_id: str = None):
    """Process audio transcript through the brain pipeline.
    
    Args:
        audio_id: UUID of the audio file to process
        job_id: UUID of the associated job
        
    Returns:
        Dict with processing results
    """
    import asyncio
    
    async def _process_transcript_async():
        try:
            # Validate inputs
            if not audio_id:
                raise ValueError("audio_id is required")
            
            audio_uuid = UUID(audio_id)
            self._job_id = UUID(job_id) if job_id else None
            
            logger.info(f"Starting transcript processing for audio {audio_id}")
            
            # Step 1: Load transcript from database
            self.log_progress(1, 6, "Loading transcript from database")
            
            # For sync operations with the legacy synchronous AudioFile model
            # We'll need to create a simple sync query method
            from core.database import get_db_session
            from models.audio_file import AudioFile
            
            db_session = next(get_db_session())
            try:
                audio_file = db_session.query(AudioFile).filter(AudioFile.id == audio_uuid).first()
                
                if not audio_file:
                    raise ValueError(f"Audio file {audio_id} not found")
                
                if not audio_file.improved_transcript:
                    raise ValueError(f"No transcript found for audio file {audio_id}")
                
                # Step 2: Chunk the transcript
                self.log_progress(2, 6, "Chunking transcript")
                
                from services.chunking_service import ChunkingService
                chunker = ChunkingService()
                chunks = chunker.chunk_text(audio_file.improved_transcript)
                
                logger.info(f"Created {len(chunks)} chunks from transcript")
                
                # Step 3: Extract entities
                self.log_progress(3, 6, "Extracting entities")
                
                from services.ner_service import NERService
                ner_service = NERService()
                
                all_entities = []
                for chunk in chunks:
                    entities = ner_service.extract_entities(
                        chunk.text, 
                        language=audio_file.language or 'en'
                    )
                    all_entities.extend(entities)
                
                logger.info(f"Extracted {len(all_entities)} entities")
                
                # Step 4: Generate embeddings and store in ChromaDB
                self.log_progress(4, 6, "Generating embeddings and storing in ChromaDB")
                
                chunk_ids = []
                chunk_texts = []
                chunk_metadatas = []
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{audio_id}_chunk_{i}"
                    chunk_ids.append(chunk_id)
                    chunk_texts.append(chunk.text)
                    
                    metadata = {
                        "audio_id": audio_id,
                        "user_id": str(audio_file.user_id),
                        "chunk_index": i,
                        "chunk_total": len(chunks),
                        "timestamp": audio_file.upload_timestamp.isoformat() if audio_file.upload_timestamp else None,
                        "language": audio_file.language,
                        "tags": audio_file.tag,
                        "category": audio_file.category,
                        "entity_count": len([e for e in all_entities if chunk.start <= e.get('start', 0) < chunk.end]),
                        "start_pos": chunk.start,
                        "end_pos": chunk.end
                    }
                    chunk_metadatas.append(metadata)
                
                # Add to ChromaDB (async call)
                await self.chromadb_client.add_documents(
                    documents=chunk_texts,
                    metadatas=chunk_metadatas,
                    ids=chunk_ids
                )
                
                # Step 5: Create graph nodes in Neo4j
                self.log_progress(5, 6, "Creating graph nodes in Neo4j")
                
                from services.graph_builder import GraphBuilder
                graph_builder = GraphBuilder(self.neo4j_client)
                
                # Create audio chunk nodes and entity relationships
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{audio_id}_chunk_{i}"
                    chunk_entities = [
                        e for e in all_entities 
                        if chunk.start <= e.get('start', 0) < chunk.end
                    ]
                    
                    await graph_builder.create_chunk_node(
                        chunk_id=chunk_id,
                        audio_id=audio_id,
                        text=chunk.text,
                        metadata=chunk_metadatas[i],
                        entities=chunk_entities
                    )
                
                # Step 6: Update audio file status
                self.log_progress(6, 6, "Updating audio file status")
                
                from datetime import datetime
                audio_file.vector_indexed = True
                audio_file.vector_indexed_at = datetime.utcnow()
                audio_file.graph_indexed = True
                audio_file.graph_indexed_at = datetime.utcnow()
                audio_file.entities_extracted = True
                audio_file.entities_extracted_at = datetime.utcnow()
                
                db_session.commit()
                
                result = {
                    "audio_id": audio_id,
                    "chunks_created": len(chunks),
                    "entities_extracted": len(all_entities),
                    "vector_indexed": True,
                    "graph_indexed": True,
                    "processing_completed_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Successfully processed transcript for audio {audio_id}")
                return result
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Failed to process transcript for audio {audio_id}: {e}")
            raise
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_process_transcript_async())


@app.task(base=BaseTask, bind=True)
def reprocess_transcript(self, audio_id: str, job_id: str = None):
    """Reprocess an existing transcript (e.g., after algorithm improvements).
    
    Args:
        audio_id: UUID of the audio file to reprocess
        job_id: UUID of the associated job
        
    Returns:
        Dict with reprocessing results
    """
    import asyncio
    
    async def _reprocess_transcript_async():
        try:
            logger.info(f"Starting transcript reprocessing for audio {audio_id}")
            
            # First, clean up existing data
            self.log_progress(1, 3, "Cleaning up existing data")
            
            # Remove from ChromaDB
            await self.chromadb_client.delete_documents(
                where={"audio_id": audio_id}
            )
            
            # Remove from Neo4j
            await self.neo4j_client.execute_write_query(
                "MATCH (c:AudioChunk {audio_id: $audio_id}) DETACH DELETE c",
                {"audio_id": audio_id}
            )
            
            # Reset audio file flags
            from core.database import get_db_session
            from models.audio_file import AudioFile
            
            db_session = next(get_db_session())
            try:
                audio_file = db_session.query(AudioFile).filter(AudioFile.id == UUID(audio_id)).first()
                
                if audio_file:
                    audio_file.vector_indexed = False
                    audio_file.vector_indexed_at = None
                    audio_file.graph_indexed = False
                    audio_file.graph_indexed_at = None
                    audio_file.entities_extracted = False
                    audio_file.entities_extracted_at = None
                    db_session.commit()
            finally:
                db_session.close()
            
            # Now reprocess
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
            logger.error(f"Failed to reprocess transcript for audio {audio_id}: {e}")
            raise
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_reprocess_transcript_async())