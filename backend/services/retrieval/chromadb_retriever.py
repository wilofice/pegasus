"""ChromaDB Retriever implementation for semantic search in vector embeddings."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import uuid

from services.retrieval.base import BaseRetriever, RetrievalResult, RetrievalFilter, ResultType, FilterOperator
from services.chromadb_manager import get_chromadb_manager

logger = logging.getLogger(__name__)


class ChromaDBRetriever(BaseRetriever):
    """Semantic search implementation for ChromaDB vector database."""
    
    def __init__(self, 
                 collection_name: str = "audio_transcripts",
                 similarity_threshold: float = 0.0,
                 **kwargs):
        """Initialize ChromaDB retriever.
        
        Args:
            collection_name: ChromaDB collection to search
            similarity_threshold: Minimum similarity score for results
            **kwargs: Additional arguments passed to base class
        """
        super().__init__("ChromaDBRetriever")
        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold
        self.chromadb_manager = None
    
    async def initialize(self) -> None:
        """Initialize ChromaDB connection and collection."""
        try:
            # Get ChromaDB manager instance
            self.chromadb_manager = get_chromadb_manager()
            
            # Ensure collection exists
            collection = self.chromadb_manager.ensure_collection(self.collection_name)
            logger.info(f"ChromaDB retriever initialized with collection: {self.collection_name}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB retriever: {e}")
            raise
    
    async def search(self, 
                    query: str, 
                    filters: List[RetrievalFilter] = None,
                    limit: int = 10,
                    **kwargs) -> List[RetrievalResult]:
        """Search for semantically similar content in ChromaDB.
        
        Args:
            query: Search query text
            filters: List of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional search parameters (user_id, date_from, date_to, tags, etc.)
            
        Returns:
            List of RetrievalResult objects with similarity scores
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Extract common filter parameters from kwargs for convenience
            user_id = kwargs.get('user_id')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            tags = kwargs.get('tags')
            
            # Build metadata filters for ChromaDB
            metadata_filters = self._build_metadata_filters(filters, user_id, date_from, date_to, tags)
            
            # Search using ChromaDB manager
            search_results = self.chromadb_manager.search_chunks(
                collection_name=self.collection_name,
                query=query,
                user_id=user_id,  # ChromaDB manager handles user filtering separately
                filters=metadata_filters,
                limit=limit
            )
            
            # Convert to RetrievalResult objects
            results = []
            for result in search_results:
                # Calculate similarity score from distance (ChromaDB returns distance, lower is better)
                distance = result.get('distance', 1.0)
                # Convert distance to similarity score (1 - normalized distance)
                similarity_score = max(0.0, 1.0 - distance) if distance is not None else 0.0
                
                # Apply similarity threshold
                if similarity_score < self.similarity_threshold:
                    continue
                
                # Extract metadata
                metadata = result.get('metadata', {})
                
                # Create RetrievalResult
                retrieval_result = RetrievalResult(
                    id=result.get('id', str(uuid.uuid4())),
                    type=ResultType.CHUNK,
                    content=result.get('document', ''),
                    metadata=self._clean_metadata(metadata),
                    score=similarity_score,
                    source=f"chromadb.{self.collection_name}",
                    timestamp=self._parse_timestamp(metadata.get('timestamp'))
                )
                
                # Add entity information if available
                if 'entities' in metadata:
                    retrieval_result.entities = self._parse_entities(metadata['entities'])
                
                results.append(retrieval_result)
            
            # Apply additional filters if provided
            if filters:
                results = self._apply_additional_filters(results, filters)
            
            # Sort by score (already ranked by ChromaDB, but ensure consistency)
            results = sorted(results, key=lambda r: r.score, reverse=True)
            
            logger.info(f"ChromaDB search returned {len(results)} results for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
    
    async def get_by_id(self, id: str) -> Optional[RetrievalResult]:
        """Retrieve a specific chunk by its ID.
        
        Args:
            id: Unique identifier of the chunk
            
        Returns:
            RetrievalResult if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Use ChromaDB manager to get specific chunk
            result = self.chromadb_manager.get_chunk_by_id(self.collection_name, id)
            
            if not result:
                return None
            
            # Convert to RetrievalResult
            metadata = result.get('metadata', {})
            
            retrieval_result = RetrievalResult(
                id=result.get('id', id),
                type=ResultType.CHUNK,
                content=result.get('document', ''),
                metadata=self._clean_metadata(metadata),
                score=1.0,  # Perfect match by ID
                source=f"chromadb.{self.collection_name}",
                timestamp=self._parse_timestamp(metadata.get('timestamp'))
            )
            
            # Add entity information if available
            if 'entities' in metadata:
                retrieval_result.entities = self._parse_entities(metadata['entities'])
            
            return retrieval_result
            
        except Exception as e:
            logger.error(f"Failed to get chunk by ID {id}: {e}")
            return None
    
    def _build_metadata_filters(self, 
                               filters: List[RetrievalFilter] = None,
                               user_id: str = None,
                               date_from: str = None,
                               date_to: str = None,
                               tags: List[str] = None) -> Dict[str, Any]:
        """Build metadata filters for ChromaDB query.
        
        Args:
            filters: List of RetrievalFilter objects
            user_id: User ID for data isolation
            date_from: Start date filter (ISO string or date object)
            date_to: End date filter (ISO string or date object)
            tags: List of tags to filter by
            
        Returns:
            Dictionary of metadata filters for ChromaDB
        """
        metadata_filters = {}
        
        # Add date range filters
        if date_from:
            date_from_str = date_from if isinstance(date_from, str) else date_from.isoformat()
            metadata_filters['date_from'] = date_from_str
        
        if date_to:
            date_to_str = date_to if isinstance(date_to, str) else date_to.isoformat()
            metadata_filters['date_to'] = date_to_str
        
        # Add tag filters
        if tags:
            metadata_filters['tags'] = tags
        
        # Process additional filters
        if filters:
            for filter in filters:
                if filter.operator == FilterOperator.EQUALS:
                    metadata_filters[filter.field] = filter.value
                elif filter.operator == FilterOperator.IN and isinstance(filter.value, list):
                    metadata_filters[filter.field] = filter.value
                # Note: ChromaDB has limited filter operators, so we'll apply others post-search
        
        return metadata_filters
    
    def _apply_additional_filters(self, 
                                 results: List[RetrievalResult], 
                                 filters: List[RetrievalFilter]) -> List[RetrievalResult]:
        """Apply filters that couldn't be handled by ChromaDB directly.
        
        Args:
            results: List of results to filter
            filters: List of filters to apply
            
        Returns:
            Filtered list of results
        """
        filtered_results = results
        
        for filter in filters:
            # Skip filters already handled in ChromaDB query
            if filter.operator in [FilterOperator.EQUALS, FilterOperator.IN]:
                continue
            
            # Apply the filter using base class method
            filtered_results = self._apply_single_filter(filtered_results, filter)
        
        return filtered_results
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize metadata from ChromaDB.
        
        Args:
            metadata: Raw metadata from ChromaDB
            
        Returns:
            Cleaned metadata dictionary
        """
        cleaned = {}
        
        # Standard fields we want to preserve and standardize
        field_mappings = {
            'audio_id': 'audio_id',
            'user_id': 'user_id',
            'chunk_index': 'chunk_index',
            'chunk_total': 'chunk_total',
            'start_pos': 'start_position',
            'end_pos': 'end_position',
            'language': 'language',
            'timestamp': 'created_at',
            'category': 'category',
            'tags': 'tags',
            'sentiment_score': 'sentiment_score',
            'entity_count': 'entity_count'
        }
        
        for old_key, new_key in field_mappings.items():
            if old_key in metadata:
                cleaned[new_key] = metadata[old_key]
        
        # Add any additional metadata not in the mapping
        for key, value in metadata.items():
            if key not in field_mappings and key not in cleaned:
                cleaned[key] = value
        
        return cleaned
    
    def _parse_timestamp(self, timestamp_str: str = None) -> datetime:
        """Parse timestamp string to datetime object.
        
        Args:
            timestamp_str: Timestamp string in ISO format
            
        Returns:
            Datetime object, current time if parsing fails
        """
        if not timestamp_str:
            return datetime.utcnow()
        
        try:
            if isinstance(timestamp_str, str):
                # Try different timestamp formats
                for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue
                
                # If all formats fail, try ISO parse
                from dateutil.parser import parse
                return parse(timestamp_str)
            
            return timestamp_str
            
        except Exception:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.utcnow()
    
    def _parse_entities(self, entities_data: Any) -> List[Dict[str, Any]]:
        """Parse entity information from metadata.
        
        Args:
            entities_data: Entity data from metadata
            
        Returns:
            List of entity dictionaries
        """
        if not entities_data:
            return []
        
        try:
            if isinstance(entities_data, list):
                return entities_data
            elif isinstance(entities_data, str):
                # Parse comma-separated entity names
                entity_names = [name.strip() for name in entities_data.split(',')]
                return [{'text': name, 'type': 'UNKNOWN'} for name in entity_names if name]
            else:
                return []
                
        except Exception as e:
            logger.warning(f"Failed to parse entities: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the ChromaDB collection.
        
        Returns:
            Dictionary with collection statistics
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            stats = self.chromadb_manager.get_collection_stats(self.collection_name)
            return {
                "retriever": self.name,
                "collection": self.collection_name,
                "statistics": stats,
                "similarity_threshold": self.similarity_threshold
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the ChromaDB retriever.
        
        Returns:
            Dictionary with health status information
        """
        base_health = await super().health_check()
        
        if not self._initialized:
            return {**base_health, "chromadb_status": "not_initialized"}
        
        try:
            # Check ChromaDB manager health
            manager_health = self.chromadb_manager.health_check()
            
            # Check collection accessibility
            collection_stats = await self.get_collection_stats()
            
            return {
                **base_health,
                "chromadb_status": "healthy",
                "collection": self.collection_name,
                "similarity_threshold": self.similarity_threshold,
                "manager_health": manager_health,
                "collection_stats": collection_stats.get("statistics", {})
            }
            
        except Exception as e:
            return {
                **base_health,
                "chromadb_status": "unhealthy",
                "error": str(e)
            }