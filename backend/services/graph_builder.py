"""Graph building service for Neo4j knowledge graph construction."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from services.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Service for building knowledge graph in Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize graph builder.
        
        Args:
            neo4j_client: Neo4j client instance
        """
        self.neo4j_client = neo4j_client
    
    async def create_chunk_node(
        self,
        chunk_id: str,
        audio_id: str,
        text: str,
        metadata: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> bool:
        """Create a chunk node with entity relationships.
        
        Args:
            chunk_id: Unique identifier for the chunk
            audio_id: Audio file ID this chunk belongs to
            text: Text content of the chunk
            metadata: Chunk metadata
            entities: List of entities found in this chunk
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create chunk node
            chunk_query = """
            MERGE (c:AudioChunk {id: $chunk_id})
            SET c.audio_id = $audio_id,
                c.text = $text,
                c.chunk_index = $chunk_index,
                c.chunk_total = $chunk_total,
                c.start_pos = $start_pos,
                c.end_pos = $end_pos,
                c.language = $language,
                c.tags = $tags,
                c.category = $category,
                c.timestamp = $timestamp,
                c.user_id = $user_id,
                c.entity_count = $entity_count,
                c.created_at = datetime(),
                c.updated_at = datetime()
            RETURN c.id as chunk_id
            """
            
            chunk_params = {
                "chunk_id": chunk_id,
                "audio_id": audio_id,
                "text": text,
                "chunk_index": metadata.get("chunk_index", 0),
                "chunk_total": metadata.get("chunk_total", 1),
                "start_pos": metadata.get("start_pos", 0),
                "end_pos": metadata.get("end_pos", len(text)),
                "language": metadata.get("language", "en"),
                "tags": metadata.get("tags", []) if isinstance(metadata.get("tags"), list) else [metadata.get("tags")] if metadata.get("tags") else [],
                "category": metadata.get("category"),
                "timestamp": metadata.get("timestamp"),
                "user_id": metadata.get("user_id"),
                "entity_count": len(entities)
            }
            
            result = await self.neo4j_client.execute_write_query(chunk_query, chunk_params)
            
            if not result:
                logger.error(f"Failed to create chunk node {chunk_id}")
                return False
            
            # Create entity nodes and relationships
            for entity in entities:
                await self._create_entity_relationship(chunk_id, entity)
            
            # Create temporal relationships
            await self._create_temporal_relationships(chunk_id, audio_id, metadata)
            
            logger.debug(f"Created chunk node {chunk_id} with {len(entities)} entity relationships")
            return True
            
        except Exception as e:
            logger.error(f"Error creating chunk node {chunk_id}: {e}")
            return False
    
    async def _create_entity_relationship(
        self,
        chunk_id: str,
        entity: Dict[str, Any]
    ) -> bool:
        """Create entity node and relationship to chunk.
        
        Args:
            chunk_id: ID of the chunk containing the entity
            entity: Entity information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            entity_text = entity.get("text", "").strip()
            entity_label = entity.get("label", "UNKNOWN")
            
            if not entity_text:
                return False
            
            # Normalize entity text for consistent matching
            normalized_text = entity_text.lower().strip()
            
            query = """
            MATCH (c:AudioChunk {id: $chunk_id})
            MERGE (e:Entity {normalized_text: $normalized_text, type: $entity_type})
            ON CREATE SET 
                e.text = $entity_text,
                e.label_description = $label_description,
                e.created_at = datetime(),
                e.mention_count = 1,
                e.first_seen = datetime()
            ON MATCH SET 
                e.mention_count = e.mention_count + 1,
                e.last_seen = datetime(),
                e.updated_at = datetime()
            
            MERGE (c)-[r:CONTAINS_ENTITY]->(e)
            ON CREATE SET 
                r.start_pos = $start_pos,
                r.end_pos = $end_pos,
                r.confidence = $confidence,
                r.created_at = datetime()
            
            RETURN e.text as entity_text, e.mention_count as mentions
            """
            
            params = {
                "chunk_id": chunk_id,
                "normalized_text": normalized_text,
                "entity_type": entity_label,
                "entity_text": entity_text,
                "label_description": entity.get("label_description", entity_label),
                "start_pos": entity.get("start", 0),
                "end_pos": entity.get("end", 0),
                "confidence": entity.get("confidence", 1.0)
            }
            
            result = await self.neo4j_client.execute_write_query(query, params)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error creating entity relationship for {entity.get('text', 'unknown')}: {e}")
            return False
    
    async def _create_temporal_relationships(
        self,
        chunk_id: str,
        audio_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Create temporal relationships between chunks.
        
        Args:
            chunk_id: Current chunk ID
            audio_id: Audio file ID
            metadata: Chunk metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            chunk_index = metadata.get("chunk_index", 0)
            
            # Create relationship to previous chunk
            if chunk_index > 0:
                prev_chunk_id = f"{audio_id}_chunk_{chunk_index - 1}"
                
                query = """
                MATCH (current:AudioChunk {id: $current_id})
                MATCH (prev:AudioChunk {id: $prev_id})
                MERGE (prev)-[r:FOLLOWED_BY]->(current)
                ON CREATE SET r.created_at = datetime()
                RETURN r
                """
                
                params = {
                    "current_id": chunk_id,
                    "prev_id": prev_chunk_id
                }
                
                await self.neo4j_client.execute_write_query(query, params)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating temporal relationships for {chunk_id}: {e}")
            return False
    
    async def create_topic_relationships(
        self,
        audio_id: str,
        topics: List[Dict[str, Any]]
    ) -> bool:
        """Create topic nodes and relationships.
        
        Args:
            audio_id: Audio file ID
            topics: List of identified topics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            for topic in topics:
                topic_name = topic.get("name", "").strip()
                if not topic_name:
                    continue
                
                query = """
                MATCH (chunks:AudioChunk {audio_id: $audio_id})
                MERGE (t:Topic {name: $topic_name})
                ON CREATE SET 
                    t.created_at = datetime(),
                    t.mention_count = 1
                ON MATCH SET 
                    t.mention_count = t.mention_count + 1,
                    t.updated_at = datetime()
                
                WITH t, chunks
                UNWIND chunks as chunk
                MERGE (chunk)-[r:RELATES_TO_TOPIC]->(t)
                ON CREATE SET 
                    r.relevance_score = $relevance_score,
                    r.created_at = datetime()
                
                RETURN t.name as topic, count(r) as relationships_created
                """
                
                params = {
                    "audio_id": audio_id,
                    "topic_name": topic_name,
                    "relevance_score": topic.get("relevance_score", 0.5)
                }
                
                await self.neo4j_client.execute_write_query(query, params)
            
            logger.debug(f"Created topic relationships for audio {audio_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating topic relationships for {audio_id}: {e}")
            return False
    
    async def find_similar_chunks(
        self,
        chunk_id: str,
        similarity_threshold: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find chunks with similar entities or topics.
        
        Args:
            chunk_id: Reference chunk ID
            similarity_threshold: Minimum similarity score
            limit: Maximum number of results
            
        Returns:
            List of similar chunks with similarity scores
        """
        try:
            query = """
            MATCH (c1:AudioChunk {id: $chunk_id})-[:CONTAINS_ENTITY]->(e:Entity)
            MATCH (c2:AudioChunk)-[:CONTAINS_ENTITY]->(e)
            WHERE c1 <> c2
            
            WITH c1, c2, count(e) as shared_entities,
                 size((c1)-[:CONTAINS_ENTITY]->()) as c1_entities,
                 size((c2)-[:CONTAINS_ENTITY]->()) as c2_entities
            
            WITH c1, c2, shared_entities, c1_entities, c2_entities,
                 toFloat(shared_entities) / sqrt(c1_entities * c2_entities) as similarity
            
            WHERE similarity >= $threshold
            
            RETURN c2.id as chunk_id,
                   c2.audio_id as audio_id,
                   c2.text as text,
                   c2.chunk_index as chunk_index,
                   similarity,
                   shared_entities,
                   c2_entities as total_entities
            
            ORDER BY similarity DESC
            LIMIT $limit
            """
            
            params = {
                "chunk_id": chunk_id,
                "threshold": similarity_threshold,
                "limit": limit
            }
            
            result = await self.neo4j_client.execute_read_query(query, params)
            return result or []
            
        except Exception as e:
            logger.error(f"Error finding similar chunks for {chunk_id}: {e}")
            return []
    
    async def get_entity_co_occurrences(
        self,
        entity_text: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Find entities that frequently co-occur with the given entity.
        
        Args:
            entity_text: Entity text to find co-occurrences for
            limit: Maximum number of results
            
        Returns:
            List of co-occurring entities with frequencies
        """
        try:
            query = """
            MATCH (e1:Entity {normalized_text: $entity_text})<-[:CONTAINS_ENTITY]-(c:AudioChunk)-[:CONTAINS_ENTITY]->(e2:Entity)
            WHERE e1 <> e2
            
            WITH e2, count(c) as co_occurrence_count,
                 collect(DISTINCT c.audio_id) as shared_audios
            
            RETURN e2.text as entity_text,
                   e2.type as entity_type,
                   co_occurrence_count,
                   size(shared_audios) as audio_files_count,
                   shared_audios
            
            ORDER BY co_occurrence_count DESC
            LIMIT $limit
            """
            
            params = {
                "entity_text": entity_text.lower().strip(),
                "limit": limit
            }
            
            result = await self.neo4j_client.execute_read_query(query, params)
            return result or []
            
        except Exception as e:
            logger.error(f"Error getting entity co-occurrences for {entity_text}: {e}")
            return []
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get overall graph statistics.
        
        Returns:
            Dictionary with graph statistics
        """
        try:
            stats_query = """
            MATCH (c:AudioChunk)
            OPTIONAL MATCH (e:Entity)
            OPTIONAL MATCH (t:Topic)
            OPTIONAL MATCH ()-[r:CONTAINS_ENTITY]->()
            OPTIONAL MATCH ()-[r2:FOLLOWED_BY]->()
            OPTIONAL MATCH ()-[r3:RELATES_TO_TOPIC]->()
            
            RETURN count(DISTINCT c) as total_chunks,
                   count(DISTINCT e) as total_entities,
                   count(DISTINCT t) as total_topics,
                   count(r) as entity_relationships,
                   count(r2) as temporal_relationships,
                   count(r3) as topic_relationships
            """
            
            result = await self.neo4j_client.execute_read_query(stats_query, {})
            
            if result and len(result) > 0:
                return result[0]
            
            return {
                "total_chunks": 0,
                "total_entities": 0,
                "total_topics": 0,
                "entity_relationships": 0,
                "temporal_relationships": 0,
                "topic_relationships": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}