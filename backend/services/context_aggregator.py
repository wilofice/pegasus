"""Context aggregation service for combining ChromaDB and Neo4j results."""
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from services.vector_db_client import ChromaDBClient  
from services.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


@dataclass
class ContextResult:
    """Represents a single context result with relevance information."""
    id: str
    content: str
    source_type: str  # 'vector', 'graph', 'hybrid'
    relevance_score: float
    metadata: Dict[str, Any]
    
    # Vector search specific
    vector_similarity: Optional[float] = None
    
    # Graph search specific  
    graph_relationships: Optional[List[Dict[str, Any]]] = None
    graph_distance: Optional[int] = None
    
    # Hybrid scoring
    semantic_relevance: Optional[float] = None
    structural_relevance: Optional[float] = None


@dataclass 
class AggregatedContext:
    """Aggregated context from multiple sources."""
    results: List[ContextResult]
    total_results: int
    query_metadata: Dict[str, Any]
    aggregation_strategy: str
    processing_time_ms: float


class ContextAggregator:
    """Service for aggregating context from ChromaDB and Neo4j."""
    
    def __init__(
        self, 
        chromadb_client: ChromaDBClient,
        neo4j_client: Neo4jClient,
        default_vector_weight: float = 0.7,
        default_graph_weight: float = 0.3
    ):
        """Initialize context aggregator.
        
        Args:
            chromadb_client: ChromaDB client instance
            neo4j_client: Neo4j client instance  
            default_vector_weight: Default weight for vector search results
            default_graph_weight: Default weight for graph search results
        """
        self.chromadb_client = chromadb_client
        self.neo4j_client = neo4j_client
        self.default_vector_weight = default_vector_weight
        self.default_graph_weight = default_graph_weight
    
    async def search_context(
        self,
        query: str,
        max_results: int = 20,
        vector_weight: Optional[float] = None,
        graph_weight: Optional[float] = None,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        include_related: bool = True
    ) -> AggregatedContext:
        """Search for context using multiple strategies.
        
        Args:
            query: Search query text
            max_results: Maximum number of results to return
            vector_weight: Weight for vector search results (0.0 - 1.0)
            graph_weight: Weight for graph search results (0.0 - 1.0) 
            strategy: Search strategy ('vector', 'graph', 'hybrid', 'ensemble')
            filters: Optional filters for search results
            include_related: Whether to include related entities/chunks
            
        Returns:
            AggregatedContext with combined results
        """
        start_time = datetime.now()
        
        # Use default weights if not provided
        if vector_weight is None:
            vector_weight = self.default_vector_weight
        if graph_weight is None:
            graph_weight = self.default_graph_weight
        
        # Normalize weights
        total_weight = vector_weight + graph_weight
        if total_weight > 0:
            vector_weight = vector_weight / total_weight
            graph_weight = graph_weight / total_weight
        
        try:
            if strategy == "vector":
                results = await self._vector_only_search(query, max_results, filters)
            elif strategy == "graph":
                results = await self._graph_only_search(query, max_results, filters)
            elif strategy == "hybrid":
                results = await self._hybrid_search(
                    query, max_results, vector_weight, graph_weight, filters, include_related
                )
            elif strategy == "ensemble":
                results = await self._ensemble_search(
                    query, max_results, vector_weight, graph_weight, filters
                )
            else:
                raise ValueError(f"Unknown search strategy: {strategy}")
            
            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Limit results
            results = results[:max_results]
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return AggregatedContext(
                results=results,
                total_results=len(results),
                query_metadata={
                    "query": query,
                    "strategy": strategy,
                    "vector_weight": vector_weight,
                    "graph_weight": graph_weight,
                    "filters": filters,
                    "include_related": include_related
                },
                aggregation_strategy=strategy,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error during context search: {e}")
            raise
    
    async def _vector_only_search(
        self, 
        query: str, 
        max_results: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContextResult]:
        """Perform vector-only search using ChromaDB.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of ContextResult objects
        """
        try:
            # Perform vector search
            vector_results = await self.chromadb_client.query(
                query_texts=[query],
                n_results=max_results,
                where=filters
            )
            
            results = []
            
            if vector_results and vector_results['documents']:
                documents = vector_results['documents'][0]
                metadatas = vector_results['metadatas'][0] if vector_results['metadatas'] else []
                distances = vector_results['distances'][0] if vector_results['distances'] else []
                ids = vector_results['ids'][0] if vector_results['ids'] else []
                
                for i, doc in enumerate(documents):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    distance = distances[i] if i < len(distances) else 1.0
                    similarity = max(0.0, 1.0 - distance)
                    
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    chunk_id = ids[i] if i < len(ids) else f"doc_{i}"
                    
                    result = ContextResult(
                        id=chunk_id,
                        content=doc,
                        source_type="vector",
                        relevance_score=similarity,
                        metadata=metadata,
                        vector_similarity=similarity,
                        semantic_relevance=similarity
                    )
                    results.append(result)
            
            logger.debug(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    async def _graph_only_search(
        self,
        query: str,
        max_results: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContextResult]:
        """Perform graph-only search using Neo4j.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Optional filters
            
        Returns:
            List of ContextResult objects
        """
        try:
            # Extract entities from query for graph search
            from services.ner_service import NERService
            ner_service = NERService()
            entities = ner_service.extract_entities(query)
            
            if not entities:
                logger.warning("No entities found in query for graph search")
                return []
            
            # Search for chunks related to the extracted entities
            cypher_query = """
            UNWIND $entity_texts as entity_text
            MATCH (e:Entity {normalized_text: toLower(entity_text)})<-[:CONTAINS_ENTITY]-(c:AudioChunk)
            
            OPTIONAL MATCH (c)-[:CONTAINS_ENTITY]->(related_e:Entity)
            WHERE related_e <> e
            
            WITH c, e, collect(DISTINCT related_e.text) as related_entities,
                 count(DISTINCT related_e) as entity_count
            
            RETURN c.id as chunk_id,
                   c.text as content,
                   c.audio_id as audio_id,
                   c.chunk_index as chunk_index,
                   c.language as language,
                   c.tags as tags,
                   c.category as category,
                   e.text as matched_entity,
                   related_entities,
                   entity_count
            
            ORDER BY entity_count DESC
            LIMIT $limit
            """
            
            entity_texts = [entity['text'] for entity in entities[:5]]  # Limit to top 5 entities
            
            graph_results = await self.neo4j_client.execute_read_query(
                cypher_query,
                {
                    "entity_texts": entity_texts,
                    "limit": max_results
                }
            )
            
            results = []
            
            for record in graph_results or []:
                # Calculate structural relevance based on entity matches and relationships
                entity_count = record.get('entity_count', 0)
                matched_entity = record.get('matched_entity', '')
                
                # Simple scoring based on entity relationships
                structural_score = min(1.0, entity_count / 10.0)  # Normalize to 0-1
                
                # Boost score if exact entity match
                if any(entity['text'].lower() == matched_entity.lower() for entity in entities):
                    structural_score = min(1.0, structural_score + 0.3)
                
                metadata = {
                    "audio_id": record.get('audio_id'),
                    "chunk_index": record.get('chunk_index'),
                    "language": record.get('language'),
                    "tags": record.get('tags'),
                    "category": record.get('category'),
                    "matched_entity": matched_entity,
                    "related_entities": record.get('related_entities', []),
                    "entity_count": entity_count
                }
                
                result = ContextResult(
                    id=record['chunk_id'],
                    content=record['content'],
                    source_type="graph",
                    relevance_score=structural_score,
                    metadata=metadata,
                    graph_relationships=[{
                        "matched_entity": matched_entity,
                        "related_entities": record.get('related_entities', [])
                    }],
                    graph_distance=1,  # Direct entity match
                    structural_relevance=structural_score
                )
                results.append(result)
            
            logger.debug(f"Graph search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in graph search: {e}")
            return []
    
    async def _hybrid_search(
        self,
        query: str,
        max_results: int,
        vector_weight: float,
        graph_weight: float,
        filters: Optional[Dict[str, Any]] = None,
        include_related: bool = True
    ) -> List[ContextResult]:
        """Perform hybrid search combining vector and graph results.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            vector_weight: Weight for vector search results
            graph_weight: Weight for graph search results
            filters: Optional filters
            include_related: Whether to include related chunks
            
        Returns:
            List of ContextResult objects with hybrid scoring
        """
        try:
            # Perform both searches in parallel
            vector_results = await self._vector_only_search(query, max_results * 2, filters)
            graph_results = await self._graph_only_search(query, max_results * 2, filters)
            
            # Create lookup maps
            vector_lookup = {result.id: result for result in vector_results}
            graph_lookup = {result.id: result for result in graph_results}
            
            # Get all unique chunk IDs
            all_chunk_ids = set(vector_lookup.keys()) | set(graph_lookup.keys())
            
            hybrid_results = []
            
            for chunk_id in all_chunk_ids:
                vector_result = vector_lookup.get(chunk_id)
                graph_result = graph_lookup.get(chunk_id)
                
                # Calculate hybrid score
                vector_score = vector_result.vector_similarity if vector_result else 0.0
                graph_score = graph_result.structural_relevance if graph_result else 0.0
                
                hybrid_score = (vector_weight * vector_score) + (graph_weight * graph_score)
                
                # Use the result with more complete information
                base_result = vector_result or graph_result
                
                if base_result:
                    # Merge metadata
                    merged_metadata = base_result.metadata.copy()
                    if vector_result and graph_result:
                        # Merge metadata from both sources
                        merged_metadata.update(graph_result.metadata)
                    
                    hybrid_result = ContextResult(
                        id=chunk_id,
                        content=base_result.content,
                        source_type="hybrid",
                        relevance_score=hybrid_score,
                        metadata=merged_metadata,
                        vector_similarity=vector_score,
                        graph_relationships=graph_result.graph_relationships if graph_result else None,
                        graph_distance=graph_result.graph_distance if graph_result else None,
                        semantic_relevance=vector_score,
                        structural_relevance=graph_score
                    )
                    hybrid_results.append(hybrid_result)
            
            # Add related chunks if requested
            if include_related and hybrid_results:
                related_results = await self._find_related_chunks(
                    [r.id for r in hybrid_results[:5]],  # Top 5 results
                    max_related=max_results // 4  # Up to 25% related results
                )
                hybrid_results.extend(related_results)
            
            logger.debug(f"Hybrid search returned {len(hybrid_results)} results")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []
    
    async def _ensemble_search(
        self,
        query: str,
        max_results: int,
        vector_weight: float,
        graph_weight: float,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContextResult]:
        """Perform ensemble search with multiple ranking strategies.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            vector_weight: Weight for vector search results
            graph_weight: Weight for graph search results
            filters: Optional filters
            
        Returns:
            List of ContextResult objects with ensemble scoring
        """
        try:
            # Perform hybrid search as base
            hybrid_results = await self._hybrid_search(
                query, max_results * 2, vector_weight, graph_weight, filters, False
            )
            
            # Apply additional ranking strategies
            for result in hybrid_results:
                # Time-based relevance (more recent = slightly higher score)
                time_boost = self._calculate_time_relevance(result.metadata)
                
                # Content length normalization
                length_factor = self._calculate_length_factor(result.content)
                
                # Entity density boost
                entity_boost = self._calculate_entity_density_boost(result.metadata)
                
                # Combine with original score
                ensemble_score = (
                    result.relevance_score * 0.8 +  # Base hybrid score (80%)
                    time_boost * 0.1 +              # Time relevance (10%)
                    length_factor * 0.05 +          # Length factor (5%)
                    entity_boost * 0.05             # Entity density (5%)
                )
                
                result.relevance_score = min(1.0, ensemble_score)
                result.source_type = "ensemble"
            
            logger.debug(f"Ensemble search returned {len(hybrid_results)} results")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Error in ensemble search: {e}")
            return []
    
    async def _find_related_chunks(
        self, 
        chunk_ids: List[str], 
        max_related: int = 5
    ) -> List[ContextResult]:
        """Find chunks related to the given chunk IDs.
        
        Args:
            chunk_ids: List of chunk IDs to find related chunks for
            max_related: Maximum number of related chunks to return
            
        Returns:
            List of related ContextResult objects
        """
        try:
            cypher_query = """
            UNWIND $chunk_ids as chunk_id
            MATCH (c1:AudioChunk {id: chunk_id})-[:CONTAINS_ENTITY]->(e:Entity)
            MATCH (c2:AudioChunk)-[:CONTAINS_ENTITY]->(e)
            WHERE c1 <> c2 AND NOT c2.id IN $chunk_ids
            
            WITH c2, count(DISTINCT e) as shared_entities
            WHERE shared_entities >= 2
            
            RETURN c2.id as chunk_id,
                   c2.text as content,
                   c2.audio_id as audio_id,
                   c2.chunk_index as chunk_index,
                   shared_entities
            
            ORDER BY shared_entities DESC
            LIMIT $limit
            """
            
            related_records = await self.neo4j_client.execute_read_query(
                cypher_query,
                {
                    "chunk_ids": chunk_ids,
                    "limit": max_related
                }
            )
            
            related_results = []
            
            for record in related_records or []:
                shared_count = record.get('shared_entities', 0)
                relevance_score = min(0.8, shared_count / 10.0)  # Related chunks get lower max score
                
                result = ContextResult(
                    id=record['chunk_id'],
                    content=record['content'],
                    source_type="related",
                    relevance_score=relevance_score,
                    metadata={
                        "audio_id": record.get('audio_id'),
                        "chunk_index": record.get('chunk_index'),
                        "shared_entities": shared_count,
                        "relation_type": "entity_overlap"
                    },
                    structural_relevance=relevance_score
                )
                related_results.append(result)
            
            logger.debug(f"Found {len(related_results)} related chunks")
            return related_results
            
        except Exception as e:
            logger.error(f"Error finding related chunks: {e}")
            return []
    
    def _calculate_time_relevance(self, metadata: Dict[str, Any]) -> float:
        """Calculate time-based relevance boost.
        
        Args:
            metadata: Chunk metadata
            
        Returns:
            Time relevance score (0.0 - 1.0)
        """
        try:
            timestamp_str = metadata.get('timestamp')
            if not timestamp_str:
                return 0.5  # Neutral score for unknown time
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timestamp.tzinfo)
            
            # Calculate age in days
            age_days = (now - timestamp).days
            
            # More recent content gets higher score (exponential decay)
            time_score = max(0.0, 1.0 - (age_days / 365.0))  # Full score for content < 1 year old
            
            return time_score
            
        except Exception:
            return 0.5  # Neutral score on error
    
    def _calculate_length_factor(self, content: str) -> float:
        """Calculate content length normalization factor.
        
        Args:
            content: Chunk content
            
        Returns:
            Length factor (0.0 - 1.0)
        """
        # Prefer chunks with moderate length (not too short, not too long)
        length = len(content)
        
        if length < 50:
            return 0.3  # Too short
        elif length < 200:
            return 1.0  # Optimal length
        elif length < 500:
            return 0.8  # Good length
        elif length < 1000:
            return 0.6  # Long but acceptable
        else:
            return 0.4  # Too long
    
    def _calculate_entity_density_boost(self, metadata: Dict[str, Any]) -> float:
        """Calculate entity density boost.
        
        Args:
            metadata: Chunk metadata
            
        Returns:
            Entity density boost (0.0 - 1.0)
        """
        try:
            entity_count = metadata.get('entity_count', 0)
            chunk_length = len(metadata.get('content', ''))
            
            if chunk_length == 0:
                return 0.0
            
            # Calculate entities per 100 characters
            entity_density = (entity_count / chunk_length) * 100
            
            # Normalize to 0-1 range (assume optimal density is around 5 entities per 100 chars)
            density_score = min(1.0, entity_density / 5.0)
            
            return density_score
            
        except Exception:
            return 0.0