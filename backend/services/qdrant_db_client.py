"""Qdrant client for Pegasus Brain vector operations."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
import asyncio
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except Exception:  # pragma: no cover - dependency optional
    QdrantClient = None

from core.config import settings
from services.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


class QdrantDBClient:
    """Qdrant client with async support for Celery tasks."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        embedding_model: str = None
    ):
        self.host = host or getattr(settings, 'qdrant_host', 'localhost')
        self.port = port or getattr(settings, 'qdrant_port', 6333)
        self.collection_name = collection_name or getattr(settings, 'qdrant_collection_name', 'pegasus_transcripts')
        self.embedding_model = embedding_model or getattr(settings, 'embedding_model', 'all-MiniLM-L6-v2')
        
        self._manager = None
    
    def connect(self) -> None:
        """Initialize Qdrant client connection."""
        if QdrantClient is None:
            raise RuntimeError("qdrant-client package not installed")
        
        try:
            self._manager = QdrantManager()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Qdrant connection."""
        try:
            if not self._manager:
                return {"status": "unhealthy", "error": "Client not connected"}
            
            stats = self._manager.get_collection_stats()
            
            return {
                "status": "healthy",
                "collection": self.collection_name,
                "vectors_count": stats.get('vectors_count', 0),
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection_name: str = None
    ) -> None:
        """Add documents to the collection."""
        if not self._manager:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        
        try:
            # Prepare chunks for Qdrant
            chunks = []
            for i, (doc, metadata, doc_id) in enumerate(zip(documents, metadatas, ids)):
                chunk = {
                    'id': doc_id,
                    'text': doc,
                    **metadata  # Include all metadata fields
                }
                chunks.append(chunk)
            
            # Add to Qdrant
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._manager.add_chunks(chunks)
            )
            logger.info(f"Added {len(documents)} documents to Qdrant")
            
        except Exception as e:
            logger.error(f"Failed to add documents to Qdrant: {e}")
            raise
    
    async def query_documents(
        self,
        query_texts: List[str] = None,
        query_embeddings: List[List[float]] = None,
        n_results: int = 10,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
        include: List[str] = None,
        collection_name: str = None
    ) -> Dict[str, Any]:
        """Query documents from the collection."""
        if not self._manager:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        
        if not query_texts:
            raise ValueError("query_texts must be provided for Qdrant search")
        
        try:
            # For now, we'll use the first query text
            query = query_texts[0] if isinstance(query_texts, list) else query_texts
            
            # Extract filters from where clause
            filters = {}
            if where:
                if 'user_id' in where:
                    filters['user_id'] = where['user_id']
                if 'audio_id' in where:
                    filters['audio_id'] = where['audio_id']
                if 'tags' in where:
                    filters['tags'] = where['tags']
            
            # Run search
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._manager.search_chunks(
                    query=query,
                    user_id=filters.get('user_id'),
                    limit=n_results,
                    filters=filters
                )
            )
            
            # Format results to match ChromaDB structure
            formatted_results = {
                'ids': [[r['id'] for r in results]],
                'documents': [[r.get('text', '') for r in results]],
                'metadatas': [[{k: v for k, v in r.items() if k not in ['id', 'text', 'score']} for r in results]],
                'distances': [[1 - r.get('score', 0) for r in results]]  # Convert similarity to distance
            }
            
            logger.debug(f"Query returned {len(results)} results from Qdrant")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    async def update_documents(
        self,
        ids: List[str],
        documents: List[str] = None,
        metadatas: List[Dict[str, Any]] = None,
        collection_name: str = None
    ) -> None:
        """Update existing documents."""
        if not self._manager:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        
        try:
            for i, doc_id in enumerate(ids):
                updates = {}
                if documents and i < len(documents):
                    updates['text'] = documents[i]
                if metadatas and i < len(metadatas):
                    updates.update(metadatas[i])
                
                if updates:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda doc_id=doc_id, updates=updates: self._manager.update_chunk(doc_id, updates)
                    )
            
            logger.info(f"Updated {len(ids)} documents in Qdrant")
            
        except Exception as e:
            logger.error(f"Failed to update documents: {e}")
            raise
    
    async def delete_documents(
        self,
        ids: List[str] = None,
        where: Dict[str, Any] = None,
        collection_name: str = None
    ) -> None:
        """Delete documents from collection."""
        if not self._manager:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        
        try:
            if ids:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._manager.delete_chunks(ids)
                )
                logger.info(f"Deleted {len(ids)} documents from Qdrant")
            elif where and 'audio_id' in where:
                # Delete by audio_id
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._manager.delete_chunks_by_audio_id(where['audio_id'])
                )
                logger.info(f"Deleted documents for audio_id: {where['audio_id']}")
            else:
                raise ValueError("Either ids or where condition with audio_id must be provided")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    async def get_collection_info(self, collection_name: str = None) -> Dict[str, Any]:
        """Get information about a collection."""
        if not self._manager:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        
        try:
            stats = await asyncio.get_event_loop().run_in_executor(
                None,
                self._manager.get_collection_stats
            )
            
            return {
                "name": self.collection_name,
                "count": stats.get('points_count', 0),
                "vectors_count": stats.get('vectors_count', 0),
                "indexed_vectors_count": stats.get('indexed_vectors_count', 0),
                "status": stats.get('status', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e)}


# Global Qdrant client instance
_qdrant_client: Optional[QdrantDBClient] = None

def get_qdrant_client() -> QdrantDBClient:
    """Get or create the global Qdrant client instance."""
    global _qdrant_client
    
    if _qdrant_client is None:
        _qdrant_client = QdrantDBClient()
        _qdrant_client.connect()
    
    return _qdrant_client

def close_qdrant_client() -> None:
    """Close the global Qdrant client."""
    global _qdrant_client
    _qdrant_client = None