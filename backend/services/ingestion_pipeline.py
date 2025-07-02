"""Dual-Database Ingestion Pipeline for coordinated data storage across ChromaDB and Neo4j."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_

from services.chromadb_manager import get_chromadb_manager
from services.neo4j_schema import get_schema_manager
from services.graph_builder import GraphBuilder, Entity
from services.neo4j_client import get_neo4j_client
from services.ner_service import NERService
from models.audio_file import AudioFile, ProcessingStatus
from models.job import ProcessingJob, JobStatus
from repositories.audio_repository import AudioRepository
from repositories.job_repository import JobRepository
from core.database import get_db_session

logger = logging.getLogger(__name__)


class Chunk:
    """Data structure representing a transcript chunk for ingestion."""
    
    def __init__(self, 
                 text: str,
                 chunk_index: int,
                 chunk_total: int,
                 start_pos: int = 0,
                 end_pos: int = None,
                 metadata: Dict[str, Any] = None):
        self.text = text
        self.chunk_index = chunk_index
        self.chunk_total = chunk_total
        self.start_pos = start_pos
        self.end_pos = end_pos or len(text)
        self.metadata = metadata or {}
        
        # Generate unique chunk ID
        self.chunk_id = self._generate_chunk_id()
        
        # Placeholder for extracted entities
        self.entities: List[Entity] = []
    
    def _generate_chunk_id(self) -> str:
        """Generate a unique chunk ID based on metadata."""
        audio_id = self.metadata.get('audio_id', 'unknown')
        return f"{audio_id}_chunk_{self.chunk_index}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for storage."""
        return {
            'chunk_id': self.chunk_id,
            'text': self.text,
            'chunk_index': self.chunk_index,
            'chunk_total': self.chunk_total,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'metadata': self.metadata,
            'entities': [e.to_dict() for e in self.entities] if hasattr(self, 'entities') else []
        }


class IngestionPipeline:
    """Orchestrates data ingestion across PostgreSQL, ChromaDB, and Neo4j."""
    
    def __init__(self, db_session: Session = None):
        """Initialize the ingestion pipeline.
        
        Args:
            db_session: Optional database session for PostgreSQL
        """
        self.db_session = db_session
        self.chromadb_manager = None
        self.neo4j_client = None
        self.graph_builder = None
        self.schema_manager = None
        self.ner_service = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all database connections and services."""
        if self._initialized:
            return
        
        try:
            # Initialize ChromaDB manager
            self.chromadb_manager = get_chromadb_manager()
            logger.info("ChromaDB manager initialized")
            
            # Initialize Neo4j client and services
            self.neo4j_client = await get_neo4j_client()
            self.graph_builder = GraphBuilder(self.neo4j_client)
            self.schema_manager = get_schema_manager()
            logger.info("Neo4j services initialized")
            
            # Ensure Neo4j schema is ready
            await self.schema_manager.initialize()
            logger.info("Neo4j schema verified")
            
            # Initialize NER service
            self.ner_service = NERService()
            logger.info("NER service initialized")
            
            self._initialized = True
            logger.info("Ingestion pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ingestion pipeline: {e}")
            raise
    
    async def ingest_transcript(self, 
                               audio_id: str, 
                               chunks: List[Chunk],
                               user_id: str = None,
                               job_id: UUID = None) -> Dict[str, Any]:
        """Ingest transcript chunks into both ChromaDB and Neo4j with transaction management.
        
        This is the main method required by Task 14.
        
        Args:
            audio_id: Audio file identifier
            chunks: List of Chunk objects to ingest
            user_id: User identifier for data isolation
            job_id: Optional job ID for tracking progress
            
        Returns:
            Dictionary with ingestion results and statistics
        """
        if not self._initialized:
            await self.initialize()
        
        # Start timing
        start_time = datetime.utcnow()
        
        # Initialize result tracking
        result = {
            "success": False,
            "audio_id": audio_id,
            "chunks_processed": 0,
            "entities_extracted": 0,
            "chromadb_stored": 0,
            "neo4j_nodes_created": 0,
            "neo4j_relationships_created": 0,
            "errors": [],
            "start_time": start_time.isoformat(),
            "duration_seconds": 0
        }
        
        # Get or create database session
        if not self.db_session:
            self.db_session = next(get_db_session())
        
        audio_repo = AudioRepository(self.db_session)
        job_repo = JobRepository(self.db_session) if job_id else None
        
        try:
            # Step 1: Begin PostgreSQL transaction
            logger.info(f"Starting ingestion for audio {audio_id} with {len(chunks)} chunks")
            
            # Update audio file status
            audio_file = audio_repo.get_by_id(audio_id)
            if not audio_file:
                raise ValueError(f"Audio file {audio_id} not found")
            
            audio_repo.update_processing_status(
                audio_id, 
                ProcessingStatus.PROCESSING,
                "Starting dual-database ingestion"
            )
            
            # Update job status if provided
            if job_repo and job_id:
                job_repo.update_job_status(
                    job_id,
                    JobStatus.PROCESSING,
                    "Ingesting transcript into vector and graph databases"
                )
            
            # Step 2: Extract entities from chunks
            logger.info("Extracting entities from chunks")
            for chunk in chunks:
                try:
                    # Extract entities using NER service
                    entities = await self._extract_entities_from_chunk(chunk)
                    chunk.entities = entities
                    result["entities_extracted"] += len(entities)
                except Exception as e:
                    logger.warning(f"Entity extraction failed for chunk {chunk.chunk_index}: {e}")
                    result["errors"].append(f"Entity extraction error in chunk {chunk.chunk_index}: {str(e)}")
            
            # Step 3: Store chunks in ChromaDB with embeddings
            logger.info("Storing chunks in ChromaDB")
            chromadb_result = await self._store_in_chromadb(audio_id, chunks, user_id)
            result["chromadb_stored"] = chromadb_result["chunks_stored"]
            
            if not chromadb_result["success"]:
                raise Exception(f"ChromaDB storage failed: {chromadb_result.get('error', 'Unknown error')}")
            
            # Step 4: Create graph nodes in Neo4j
            logger.info("Creating graph nodes in Neo4j")
            neo4j_result = await self._create_graph_nodes(audio_id, chunks, user_id)
            result["neo4j_nodes_created"] = neo4j_result["nodes_created"]
            result["neo4j_relationships_created"] = neo4j_result["relationships_created"]
            
            if not neo4j_result["success"]:
                raise Exception(f"Neo4j graph creation failed: {neo4j_result.get('error', 'Unknown error')}")
            
            # Step 5: Update PostgreSQL with completion status
            result["chunks_processed"] = len(chunks)
            
            # Store ingestion metadata
            metadata = audio_file.metadata or {}
            metadata.update({
                "ingestion_completed": datetime.utcnow().isoformat(),
                "chunks_processed": result["chunks_processed"],
                "entities_extracted": result["entities_extracted"],
                "chromadb_stored": result["chromadb_stored"],
                "neo4j_nodes_created": result["neo4j_nodes_created"],
                "neo4j_relationships_created": result["neo4j_relationships_created"]
            })
            
            audio_repo.update(
                audio_id,
                metadata=metadata,
                processing_status=ProcessingStatus.COMPLETED
            )
            
            # Update job status if provided
            if job_repo and job_id:
                job_repo.update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    "Ingestion completed successfully",
                    result_data=result
                )
            
            # Commit PostgreSQL transaction
            self.db_session.commit()
            
            # Calculate duration
            end_time = datetime.utcnow()
            result["duration_seconds"] = (end_time - start_time).total_seconds()
            result["success"] = True
            result["end_time"] = end_time.isoformat()
            
            logger.info(f"Successfully ingested {result['chunks_processed']} chunks for audio {audio_id}")
            
        except Exception as e:
            # Rollback on failure
            logger.error(f"Ingestion failed for audio {audio_id}: {e}")
            result["errors"].append(f"Pipeline error: {str(e)}")
            
            # Rollback PostgreSQL
            self.db_session.rollback()
            
            # Update status to failed
            audio_repo.update_processing_status(
                audio_id,
                ProcessingStatus.FAILED,
                f"Ingestion failed: {str(e)}"
            )
            
            if job_repo and job_id:
                job_repo.update_job_status(
                    job_id,
                    JobStatus.FAILED,
                    f"Ingestion failed: {str(e)}",
                    error_message=str(e)
                )
            
            self.db_session.commit()
            
            # Attempt cleanup
            await self._cleanup_partial_ingestion(audio_id, result)
            
            raise
        
        return result
    
    async def _extract_entities_from_chunk(self, chunk: Chunk) -> List[Entity]:
        """Extract entities from a chunk using NER service."""
        try:
            # Determine language from chunk metadata
            language = chunk.metadata.get('language', 'en')
            
            # Use the NER service to extract entities
            entities_data = self.ner_service.extract_entities(
                text=chunk.text,
                language=language,
                include_positions=True
            )
            
            # Convert to Entity objects
            entities = []
            for entity_data in entities_data:
                entity = Entity(
                    text=entity_data['text'],
                    label=entity_data['label'],
                    start=entity_data.get('start', 0) + chunk.start_pos,
                    end=entity_data.get('end', 0) + chunk.start_pos,
                    confidence=entity_data.get('confidence', 1.0),
                    metadata={
                        'chunk_index': chunk.chunk_index,
                        'source': 'ner_service',
                        'label_description': entity_data.get('label_description', entity_data['label'])
                    }
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed for chunk: {e}")
            return []
    
    async def _store_in_chromadb(self, audio_id: str, chunks: List[Chunk], 
                                user_id: str = None) -> Dict[str, Any]:
        """Store chunks in ChromaDB with metadata and embeddings."""
        try:
            collection_name = "audio_transcripts"
            
            # Prepare chunks for ChromaDB
            chromadb_chunks = []
            for chunk in chunks:
                chunk_data = {
                    "text": chunk.text,
                    "metadata": {
                        "chunk_index": chunk.chunk_index,
                        "chunk_total": chunk.chunk_total,
                        "start_pos": chunk.start_pos,
                        "end_pos": chunk.end_pos,
                        **chunk.metadata
                    }
                }
                
                # Add entity information
                if chunk.entities:
                    chunk_data["entities"] = [
                        {"text": e.text, "type": e.label}
                        for e in chunk.entities[:10]  # Limit for metadata
                    ]
                    chunk_data["metadata"]["entity_count"] = len(chunk.entities)
                
                chromadb_chunks.append(chunk_data)
            
            # Store in ChromaDB
            success = self.chromadb_manager.add_transcript_chunks(
                collection_name=collection_name,
                chunks=chromadb_chunks,
                audio_id=audio_id,
                user_id=user_id,
                metadata={
                    "ingestion_time": datetime.utcnow().isoformat(),
                    "total_chunks": len(chunks)
                }
            )
            
            return {
                "success": success,
                "chunks_stored": len(chunks) if success else 0
            }
            
        except Exception as e:
            logger.error(f"ChromaDB storage failed: {e}")
            return {
                "success": False,
                "chunks_stored": 0,
                "error": str(e)
            }
    
    async def _create_graph_nodes(self, audio_id: str, chunks: List[Chunk], 
                                 user_id: str = None) -> Dict[str, Any]:
        """Create nodes and relationships in Neo4j."""
        try:
            total_nodes = 0
            total_relationships = 0
            
            # Create audio file node
            audio_node_query = """
            MERGE (a:AudioFile {id: $audio_id})
            ON CREATE SET 
                a.created_at = datetime(),
                a.user_id = $user_id
            RETURN a.id as audio_id
            """
            
            await self.neo4j_client.execute_write_query(
                audio_node_query,
                {"audio_id": audio_id, "user_id": user_id}
            )
            
            # Process each chunk
            for chunk in chunks:
                # Create chunk node with full metadata
                chunk_result = await self.graph_builder.create_chunk_node(
                    chunk_id=chunk.chunk_id,
                    audio_id=audio_id,
                    text=chunk.text,
                    metadata={
                        **chunk.metadata,
                        "chunk_index": chunk.chunk_index,
                        "chunk_total": chunk.chunk_total,
                        "start_pos": chunk.start_pos,
                        "end_pos": chunk.end_pos,
                        "user_id": user_id
                    },
                    entities=[e.to_dict() for e in chunk.entities]
                )
                
                if chunk_result:
                    total_nodes += 1
                
                # Create entity nodes and relationships
                if chunk.entities:
                    entity_result = await self.graph_builder.create_entity_nodes(
                        entities=chunk.entities,
                        chunk_id=chunk.chunk_id,
                        user_id=user_id,
                        audio_id=audio_id
                    )
                    
                    if entity_result["success"]:
                        total_nodes += entity_result.get("entities_created", 0)
                        total_relationships += entity_result.get("relationships_created", 0)
            
            # Create temporal relationships between chunks
            await self._create_temporal_chunk_relationships(audio_id, chunks)
            total_relationships += len(chunks) - 1  # Sequential relationships
            
            return {
                "success": True,
                "nodes_created": total_nodes,
                "relationships_created": total_relationships
            }
            
        except Exception as e:
            logger.error(f"Neo4j graph creation failed: {e}")
            return {
                "success": False,
                "nodes_created": 0,
                "relationships_created": 0,
                "error": str(e)
            }
    
    async def _create_temporal_chunk_relationships(self, audio_id: str, chunks: List[Chunk]):
        """Create FOLLOWED_BY relationships between sequential chunks."""
        try:
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]
                
                query = """
                MATCH (c1:AudioChunk {id: $current_id})
                MATCH (c2:AudioChunk {id: $next_id})
                MERGE (c1)-[r:FOLLOWED_BY]->(c2)
                ON CREATE SET 
                    r.created_at = datetime(),
                    r.sequence_order = $order
                RETURN r
                """
                
                params = {
                    "current_id": current_chunk.chunk_id,
                    "next_id": next_chunk.chunk_id,
                    "order": i
                }
                
                await self.neo4j_client.execute_write_query(query, params)
                
        except Exception as e:
            logger.error(f"Failed to create temporal relationships: {e}")
    
    async def _cleanup_partial_ingestion(self, audio_id: str, result: Dict[str, Any]):
        """Attempt to clean up partial ingestion on failure."""
        logger.info(f"Attempting cleanup for failed ingestion of audio {audio_id}")
        
        try:
            # Clean up ChromaDB entries
            if result.get("chromadb_stored", 0) > 0:
                self.chromadb_manager.delete_audio_chunks("audio_transcripts", audio_id)
                logger.info(f"Cleaned up {result['chromadb_stored']} chunks from ChromaDB")
            
            # Clean up Neo4j nodes
            if result.get("neo4j_nodes_created", 0) > 0:
                cleanup_query = """
                MATCH (c:AudioChunk {audio_id: $audio_id})
                DETACH DELETE c
                """
                await self.neo4j_client.execute_write_query(
                    cleanup_query,
                    {"audio_id": audio_id}
                )
                logger.info(f"Cleaned up Neo4j nodes for audio {audio_id}")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    async def verify_ingestion(self, audio_id: str, user_id: str = None) -> Dict[str, Any]:
        """Verify that ingestion was successful across all databases."""
        verification = {
            "audio_id": audio_id,
            "postgresql": {"status": "unknown", "details": {}},
            "chromadb": {"status": "unknown", "details": {}},
            "neo4j": {"status": "unknown", "details": {}},
            "overall_status": "unknown"
        }
        
        try:
            # Verify PostgreSQL
            audio_repo = AudioRepository(self.db_session)
            audio_file = audio_repo.get_by_id(audio_id)
            
            if audio_file:
                verification["postgresql"]["status"] = "found"
                verification["postgresql"]["details"] = {
                    "processing_status": audio_file.processing_status.value,
                    "chunks_processed": audio_file.metadata.get("chunks_processed", 0),
                    "entities_extracted": audio_file.metadata.get("entities_extracted", 0)
                }
            else:
                verification["postgresql"]["status"] = "not_found"
            
            # Verify ChromaDB
            search_results = self.chromadb_manager.search_chunks(
                collection_name="audio_transcripts",
                query="test",
                user_id=user_id,
                filters={"audio_id": audio_id},
                limit=1
            )
            
            verification["chromadb"]["status"] = "found" if search_results else "not_found"
            verification["chromadb"]["details"] = {
                "chunks_found": len(search_results)
            }
            
            # Verify Neo4j
            neo4j_query = """
            MATCH (c:AudioChunk {audio_id: $audio_id})
            RETURN count(c) as chunk_count
            """
            
            neo4j_result = await self.neo4j_client.execute_query(
                neo4j_query,
                {"audio_id": audio_id}
            )
            
            chunk_count = neo4j_result[0]["chunk_count"] if neo4j_result else 0
            verification["neo4j"]["status"] = "found" if chunk_count > 0 else "not_found"
            verification["neo4j"]["details"] = {
                "chunks_found": chunk_count
            }
            
            # Determine overall status
            all_found = all(
                db["status"] == "found" 
                for db in [verification["postgresql"], verification["chromadb"], verification["neo4j"]]
            )
            verification["overall_status"] = "complete" if all_found else "incomplete"
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            verification["error"] = str(e)
            verification["overall_status"] = "error"
        
        return verification


def get_ingestion_pipeline(db_session: Session = None) -> IngestionPipeline:
    """Get an instance of the ingestion pipeline.
    
    Args:
        db_session: Optional database session
        
    Returns:
        IngestionPipeline instance
    """
    return IngestionPipeline(db_session)