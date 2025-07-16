"""
Qdrant vector database manager for storing and retrieving transcript chunks.
Replaces ChromaDB with Qdrant for better performance and features.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, Range, MatchValue,
    SearchRequest, ScoredPoint
)
from sentence_transformers import SentenceTransformer

from core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manager class for Qdrant vector database operations."""
    
    def __init__(self):
        """Initialize Qdrant client and embedding model."""
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=30
        )
        self.collection_name = settings.qdrant_collection_name
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
        
        # Create collection if it doesn't exist
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists in Qdrant."""
        try:
            collections = self.client.get_collections().collections
            if not any(col.name == self.collection_name for col in collections):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Add transcript chunks to Qdrant.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and metadata
            
        Returns:
            List of chunk IDs
        """
        if not chunks:
            return []
        
        try:
            # Generate embeddings
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_model.encode(texts).tolist()
            
            # Prepare points
            points = []
            chunk_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = chunk.get('id', str(uuid.uuid4()))
                chunk_ids.append(chunk_id)
                
                # Prepare metadata
                metadata = {
                    'text': chunk['text'],
                    'audio_id': chunk.get('audio_id', ''),
                    'user_id': chunk.get('user_id', ''),
                    'chunk_index': chunk.get('chunk_index', i),
                    'timestamp': chunk.get('timestamp', datetime.utcnow().isoformat()),
                    'language': chunk.get('language', 'unknown'),
                    'sentiment_score': chunk.get('sentiment_score', 0.0),
                    'entities': chunk.get('entities', []),
                    'tags': chunk.get('tags', []),
                    'category': chunk.get('category', ''),
                }
                
                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=metadata
                )
                points.append(point)
            
            # Upsert points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Added {len(chunks)} chunks to Qdrant")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Error adding chunks to Qdrant: {e}")
            raise
    
    def search_chunks(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using semantic similarity.
        
        Args:
            query: Search query text
            user_id: Optional user ID filter
            limit: Maximum number of results
            filters: Additional filters
            
        Returns:
            List of matching chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build filter conditions
            filter_conditions = []
            
            if user_id:
                filter_conditions.append(
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                )
            
            if filters:
                # Add date range filter
                if 'start_date' in filters and 'end_date' in filters:
                    # Note: For date filtering, you'd need to store timestamps as numbers
                    pass
                
                # Add tag filter
                if 'tags' in filters:
                    for tag in filters['tags']:
                        filter_conditions.append(
                            FieldCondition(
                                key="tags",
                                match=MatchValue(value=tag)
                            )
                        )
            
            # Perform search
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter
            )
            
            # Format results
            chunks = []
            for result in results:
                chunk = result.payload.copy()
                chunk['score'] = result.score
                chunk['id'] = result.id
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error searching chunks in Qdrant: {e}")
            raise
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID."""
        try:
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id]
            )
            
            if points:
                point = points[0]
                chunk = point.payload.copy()
                chunk['id'] = point.id
                return chunk
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting chunk by ID: {e}")
            raise
    
    def update_chunk(self, chunk_id: str, updates: Dict[str, Any]) -> bool:
        """Update a chunk's metadata."""
        try:
            # Get existing chunk
            existing = self.get_chunk_by_id(chunk_id)
            if not existing:
                return False
            
            # Update metadata
            existing.update(updates)
            
            # Update in Qdrant
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=existing,
                points=[chunk_id]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating chunk: {e}")
            raise
    
    def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """Delete chunks by IDs."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids
            )
            logger.info(f"Deleted {len(chunk_ids)} chunks from Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise
    
    def delete_chunks_by_audio_id(self, audio_id: str) -> int:
        """Delete all chunks for a specific audio ID."""
        try:
            # Search for chunks with this audio_id
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="audio_id",
                        match=MatchValue(value=audio_id)
                    )
                ]
            )
            
            # Delete matching points
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_condition
            )
            
            logger.info(f"Deleted chunks for audio_id: {audio_id}")
            return result.operation_id
            
        except Exception as e:
            logger.error(f"Error deleting chunks by audio_id: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                'vectors_count': info.vectors_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'points_count': info.points_count,
                'segments_count': info.segments_count,
                'status': info.status,
                'config': {
                    'vector_size': info.config.params.vectors.size,
                    'distance': info.config.params.vectors.distance
                }
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise