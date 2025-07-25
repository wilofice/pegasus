"""Celery tasks for processing conversation history."""
import logging
import asyncio
from uuid import UUID

from workers.celery_app import app
from workers.base_task import BaseTask

logger = logging.getLogger(__name__)


@app.task(base=BaseTask, bind=True)
def process_conversation_history(self, conversation_history_id: str, job_id: str = None):
    """Processes a single conversation history entry."""
    
    async def _process_async():
        from core.database import async_session
        from repositories.conversation_history_repository import ConversationHistoryRepository
        from services.chunking_service import ChunkingService
        from services.ner_service import NERService
        from services.sentiment_service import SentimentService
        from services.graph_builder import GraphBuilder
        
        self._job_id = UUID(job_id) if job_id else None
        conversation_history_uuid = UUID(conversation_history_id)
        
        async with async_session() as db:
            repo = ConversationHistoryRepository(db)
            history_entry = await repo.get_by_id(conversation_history_uuid)
            
            if not history_entry:
                logger.error(f"Conversation history with ID {conversation_history_id} not found.")
                return
            
            text_to_process = f"User: {history_entry.user_message}\nAssistant: {history_entry.assistant_response}"
            
            # The rest of the pipeline is similar to the transcript processor
            chunker = ChunkingService()
            chunks = chunker.chunk_text(text_to_process)
            
            ner_service = NERService()
            sentiment_service = SentimentService()
            graph_builder = GraphBuilder(self.neo4j_client)
            
            all_entities = []
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                entities = ner_service.extract_entities(chunk.text)
                all_entities.extend(entities)
                
                sentiment = sentiment_service.analyze_sentiment(chunk.text)
                
                metadata = {
                    "conversation_history_id": str(conversation_history_id),
                    "user_id": str(history_entry.user_id),
                    "session_id": str(history_entry.session_id),
                    "chunk_index": i,
                    "chunk_total": len(chunks),
                    "timestamp": history_entry.timestamp.isoformat(),
                    "entity_count": len(entities),
                    "sentiment_score": sentiment["score"],
                    "sentiment_classification": sentiment["classification"]
                }
                chunk_metadatas.append(metadata)
            
            # Add to ChromaDB
            await self.chromadb_client.add_documents(
                documents=[c.text for c in chunks],
                metadatas=chunk_metadatas,
                ids=[f"{conversation_history_id}_chunk_{i}" for i in range(len(chunks))]
            )
            
            # Add to Neo4j
            for i, chunk in enumerate(chunks):
                chunk_id = f"{conversation_history_id}_chunk_{i}"
                chunk_entities = [e for e in all_entities if chunk.start <= e.get('start', 0) < chunk.end]
                
                await graph_builder.create_chunk_node(
                    chunk_id=chunk_id,
                    audio_id=None,  # Not from an audio file
                    text=chunk.text,
                    metadata=chunk_metadatas[i],
                    entities=chunk_entities
                )
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_process_async())