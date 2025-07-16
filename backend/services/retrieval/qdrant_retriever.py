"""
Qdrant-based retriever for semantic search.
Implements the BaseRetriever interface for Qdrant vector database.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.retrieval.base import BaseRetriever
from services.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


class QdrantRetriever(BaseRetriever):
    """Retriever implementation using Qdrant for semantic search."""
    
    def __init__(self):
        """Initialize Qdrant retriever."""
        self.qdrant_manager = QdrantManager()
        logger.info("Initialized QdrantRetriever")
    
    async def retrieve(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using Qdrant semantic search.
        
        Args:
            query: Search query
            user_id: Optional user ID filter
            limit: Maximum number of results
            filters: Additional filters (date_range, tags, etc.)
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            # Perform semantic search
            results = self.qdrant_manager.search_chunks(
                query=query,
                user_id=user_id,
                limit=limit,
                filters=filters
            )
            
            # Format results according to base interface
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result.get('id'),
                    'content': result.get('text', ''),
                    'metadata': {
                        'audio_id': result.get('audio_id'),
                        'user_id': result.get('user_id'),
                        'chunk_index': result.get('chunk_index'),
                        'timestamp': result.get('timestamp'),
                        'language': result.get('language'),
                        'sentiment_score': result.get('sentiment_score'),
                        'entities': result.get('entities', []),
                        'tags': result.get('tags', []),
                        'category': result.get('category', ''),
                    },
                    'score': result.get('score', 0.0),
                    'source': 'qdrant'
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Retrieved {len(formatted_results)} results from Qdrant for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error retrieving from Qdrant: {e}")
            return []
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> List[str]:
        """
        Add documents to Qdrant.
        
        Args:
            documents: List of documents to add
            user_id: Optional user ID to associate with documents
            
        Returns:
            List of document IDs
        """
        try:
            # Format documents for Qdrant
            chunks = []
            for doc in documents:
                chunk = {
                    'text': doc.get('content', ''),
                    'audio_id': doc.get('metadata', {}).get('audio_id', ''),
                    'user_id': user_id or doc.get('metadata', {}).get('user_id', ''),
                    'chunk_index': doc.get('metadata', {}).get('chunk_index', 0),
                    'timestamp': doc.get('metadata', {}).get('timestamp', datetime.utcnow().isoformat()),
                    'language': doc.get('metadata', {}).get('language', 'unknown'),
                    'sentiment_score': doc.get('metadata', {}).get('sentiment_score', 0.0),
                    'entities': doc.get('metadata', {}).get('entities', []),
                    'tags': doc.get('metadata', {}).get('tags', []),
                    'category': doc.get('metadata', {}).get('category', ''),
                }
                if 'id' in doc:
                    chunk['id'] = doc['id']
                chunks.append(chunk)
            
            # Add to Qdrant
            doc_ids = self.qdrant_manager.add_chunks(chunks)
            logger.info(f"Added {len(doc_ids)} documents to Qdrant")
            return doc_ids
            
        except Exception as e:
            logger.error(f"Error adding documents to Qdrant: {e}")
            raise
    
    async def delete_documents(
        self,
        document_ids: List[str]
    ) -> bool:
        """
        Delete documents from Qdrant.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            Success status
        """
        try:
            success = self.qdrant_manager.delete_chunks(document_ids)
            logger.info(f"Deleted {len(document_ids)} documents from Qdrant")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting documents from Qdrant: {e}")
            return False
    
    async def update_document(
        self,
        document_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a document in Qdrant.
        
        Args:
            document_id: Document ID to update
            updates: Updates to apply
            
        Returns:
            Success status
        """
        try:
            # Format updates for Qdrant
            qdrant_updates = {}
            
            if 'content' in updates:
                qdrant_updates['text'] = updates['content']
            
            if 'metadata' in updates:
                metadata = updates['metadata']
                for key in ['audio_id', 'user_id', 'chunk_index', 'timestamp', 
                           'language', 'sentiment_score', 'entities', 'tags', 'category']:
                    if key in metadata:
                        qdrant_updates[key] = metadata[key]
            
            # Update in Qdrant
            success = self.qdrant_manager.update_chunk(document_id, qdrant_updates)
            logger.info(f"Updated document {document_id} in Qdrant")
            return success
            
        except Exception as e:
            logger.error(f"Error updating document in Qdrant: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the Qdrant collection."""
        try:
            stats = self.qdrant_manager.get_collection_stats()
            return {
                'source': 'qdrant',
                'stats': stats
            }
        except Exception as e:
            logger.error(f"Error getting Qdrant stats: {e}")
            return {
                'source': 'qdrant',
                'error': str(e)
            }