"""Enhanced ChromaDB management for audio transcripts."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions
try:
    # Try to import sentence transformers for testing
    import sentence_transformers
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Enhanced ChromaDB manager for audio transcript collections."""
    
    def __init__(self, client: Client = None):
        """Initialize ChromaDB manager.
        
        Args:
            client: Optional ChromaDB client instance
        """
        self.client = client
        self._collections: Dict[str, Any] = {}
        
        # Use a fallback embedding function if sentence_transformers is not available
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize SentenceTransformer, using default: {e}")
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        else:
            logger.warning("sentence_transformers not available, using default embedding function")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    def ensure_collection(self, name: str = "audio_transcripts") -> Any:
        """Create or get a collection with proper configuration.
        
        Args:
            name: Collection name
            
        Returns:
            ChromaDB collection object
        """
        if name in self._collections:
            return self._collections[name]
        
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Retrieved existing collection: {name}")
            
        except Exception:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={
                    "description": "Audio transcript chunks with metadata",
                    "created_at": datetime.utcnow().isoformat(),
                    "version": "1.0"
                }
            )
            logger.info(f"Created new collection: {name}")
        
        self._collections[name] = collection
        return collection
    
    def add_transcript_chunks(
        self,
        collection_name: str,
        chunks: List[Dict[str, Any]],
        audio_id: str,
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add transcript chunks to a collection.
        
        Args:
            collection_name: Name of the collection
            chunks: List of chunk dictionaries with 'text' and metadata
            audio_id: Audio file identifier
            user_id: User identifier
            metadata: Additional metadata for all chunks
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.ensure_collection(collection_name)
            
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            base_metadata = {
                "audio_id": audio_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            for i, chunk in enumerate(chunks):
                # Generate unique ID for chunk
                chunk_id = f"{audio_id}_chunk_{i}_{uuid.uuid4().hex[:8]}"
                ids.append(chunk_id)
                
                # Extract text content
                documents.append(chunk.get("text", ""))
                
                # Combine base metadata with chunk-specific metadata
                chunk_metadata = {
                    **base_metadata,
                    "chunk_index": i,
                    "chunk_id": chunk_id,
                    **chunk.get("metadata", {})
                }
                
                # Add optional metadata fields
                if "entities" in chunk:
                    chunk_metadata["entity_count"] = len(chunk["entities"])
                    chunk_metadata["entities"] = [e.get("text", "") for e in chunk["entities"][:5]]  # Limit to 5 entities
                
                if "sentiment_score" in chunk:
                    chunk_metadata["sentiment_score"] = chunk["sentiment_score"]
                
                if "language" in chunk:
                    chunk_metadata["language"] = chunk["language"]
                
                # Ensure all metadata values are serializable
                chunk_metadata = self._sanitize_metadata(chunk_metadata)
                metadatas.append(chunk_metadata)
            
            # Add to collection
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} chunks to collection {collection_name} for audio {audio_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to collection {collection_name}: {e}")
            return False
    
    def search_chunks(
        self,
        collection_name: str,
        query: str,
        user_id: str = None,
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for chunks in a collection.
        
        Args:
            collection_name: Name of the collection
            query: Search query text
            user_id: Optional user ID for filtering
            filters: Additional metadata filters
            limit: Maximum number of results
            
        Returns:
            List of search results with metadata
        """
        try:
            collection = self.ensure_collection(collection_name)
            
            # Build where clause for filtering
            where_clause = {}
            if user_id:
                where_clause["user_id"] = user_id
            
            if filters:
                where_clause.update(filters)
            
            # Perform search
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    result = {
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} results for query in {collection_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching collection {collection_name}: {e}")
            return []
    
    def get_chunk_by_id(self, collection_name: str, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID.
        
        Args:
            collection_name: Name of the collection
            chunk_id: Chunk identifier
            
        Returns:
            Chunk data or None if not found
        """
        try:
            collection = self.ensure_collection(collection_name)
            
            results = collection.get(ids=[chunk_id])
            
            if results["documents"] and results["documents"][0]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0],
                    "metadata": results["metadatas"][0] if results["metadatas"] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting chunk {chunk_id} from {collection_name}: {e}")
            return None
    
    def delete_audio_chunks(self, collection_name: str, audio_id: str) -> bool:
        """Delete all chunks for a specific audio file.
        
        Args:
            collection_name: Name of the collection
            audio_id: Audio file identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.ensure_collection(collection_name)
            
            # Get all chunks for this audio
            results = collection.get(where={"audio_id": audio_id})
            
            if results["ids"]:
                collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks for audio {audio_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chunks for audio {audio_id}: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection statistics
        """
        try:
            collection = self.ensure_collection(collection_name)
            
            # Get total count
            total_results = collection.get()
            total_count = len(total_results["ids"]) if total_results["ids"] else 0
            
            # Get user counts
            user_counts = {}
            if total_results["metadatas"]:
                for metadata in total_results["metadatas"]:
                    user_id = metadata.get("user_id", "unknown")
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
            
            # Get language distribution
            language_counts = {}
            if total_results["metadatas"]:
                for metadata in total_results["metadatas"]:
                    language = metadata.get("language", "unknown")
                    language_counts[language] = language_counts.get(language, 0) + 1
            
            return {
                "collection_name": collection_name,
                "total_chunks": total_count,
                "unique_users": len(user_counts),
                "user_distribution": user_counts,
                "language_distribution": language_counts,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for collection {collection_name}: {e}")
            return {}
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """List all available collections.
        
        Returns:
            List of collection information
        """
        try:
            collections = self.client.list_collections()
            
            collection_info = []
            for collection in collections:
                info = {
                    "name": collection.name,
                    "metadata": collection.metadata,
                    **self.get_collection_stats(collection.name)
                }
                collection_info.append(info)
            
            return collection_info
            
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata to ensure compatibility with ChromaDB.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Sanitized metadata
        """
        sanitized = {}
        
        for key, value in metadata.items():
            # Skip None values
            if value is None:
                continue
            
            # Convert complex types to strings
            if isinstance(value, (dict, list)):
                if isinstance(value, list) and len(value) > 0:
                    # For lists, join string elements or convert to string
                    if all(isinstance(item, str) for item in value):
                        sanitized[key] = ", ".join(value[:10])  # Limit length
                    else:
                        sanitized[key] = str(value)[:200]  # Limit length
                else:
                    sanitized[key] = str(value)[:200]  # Limit length
            
            # Keep primitives as-is
            elif isinstance(value, (str, int, float, bool)):
                if isinstance(value, str):
                    sanitized[key] = value[:500]  # Limit string length
                else:
                    sanitized[key] = value
            
            # Convert other types to string
            else:
                sanitized[key] = str(value)[:200]
        
        return sanitized
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on ChromaDB connection.
        
        Returns:
            Health check results
        """
        try:
            # Try to list collections
            collections = self.client.list_collections()
            
            return {
                "status": "healthy",
                "collections_count": len(collections),
                "client_connected": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "client_connected": False,
                "timestamp": datetime.utcnow().isoformat()
            }


def get_chromadb_manager() -> ChromaDBManager:
    """Get ChromaDB manager instance.
    
    Returns:
        ChromaDB manager instance
    """
    from services.vector_db_client import ChromaDBClient
    
    # Create and connect synchronously
    client_wrapper = ChromaDBClient()
    client_wrapper.connect()
    
    return ChromaDBManager(client=client_wrapper._client)