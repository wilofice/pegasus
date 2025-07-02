"""Enhanced ChromaDB client for Pegasus Brain vector operations."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import asyncio
from datetime import datetime

try:
    import chromadb
    from chromadb.utils import embedding_functions
    from chromadb.config import Settings
except Exception:  # pragma: no cover - dependency optional
    chromadb = None

from core.config import settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """Enhanced ChromaDB client with async support and better organization."""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        embedding_model: str = None
    ):
        self.host = host or getattr(settings, 'chromadb_host', 'localhost')
        self.port = port or getattr(settings, 'chromadb_port', 8001)
        self.collection_name = collection_name or getattr(settings, 'chromadb_collection_name', 'pegasus_transcripts')
        self.embedding_model = embedding_model or getattr(settings, 'embedding_model', 'all-MiniLM-L6-v2')
        
        self._client = None
        self._embedder = None
        self._collection = None
    
    def connect(self) -> None:
        """Initialize ChromaDB client connection."""
        if chromadb is None:
            raise RuntimeError("chromadb package not installed")
        
        try:
            # Try HTTP client first (for Docker setup)
            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Test connection
            self._client.heartbeat()
            logger.info(f"Connected to ChromaDB at {self.host}:{self.port}")
            
        except Exception as e:
            logger.warning(f"HTTP connection failed: {e}, trying persistent client")
            
            # Fallback to persistent client
            db_path = Path(__file__).resolve().parents[1] / "database"
            self._client = chromadb.PersistentClient(
                path=str(db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Connected to ChromaDB with persistent client at {db_path}")
        
        # Initialize embedding function with fallback
        try:
            self._embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
        except Exception as e:
            logger.warning(f"Failed to initialize SentenceTransformer, using default: {e}")
            self._embedder = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedder,
            metadata={
                "description": "Pegasus Brain audio transcripts and documents",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Initialized collection: {self.collection_name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on ChromaDB connection."""
        try:
            if not self._client:
                return {"status": "unhealthy", "error": "Client not connected"}
            
            heartbeat = self._client.heartbeat()
            collection_count = len(self._client.list_collections())
            
            return {
                "status": "healthy",
                "heartbeat": heartbeat,
                "collections": collection_count,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def ensure_collection(self, name: str = None) -> Any:
        """Ensure collection exists and return it."""
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        collection_name = name or self.collection_name
        
        try:
            collection = self._client.get_collection(collection_name)
            logger.debug(f"Retrieved existing collection: {collection_name}")
            return collection
        except Exception:
            # Collection doesn't exist, create it
            collection = self._client.create_collection(
                name=collection_name,
                embedding_function=self._embedder,
                metadata={
                    "description": f"Pegasus Brain collection: {collection_name}",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Created new collection: {collection_name}")
            return collection
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        collection_name: str = None
    ) -> None:
        """Add documents to the collection."""
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        collection = self.ensure_collection(collection_name)
        
        try:
            # Run in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            )
            logger.info(f"Added {len(documents)} documents to collection")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
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
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        if not query_texts and not query_embeddings:
            raise ValueError("Either query_texts or query_embeddings must be provided")
        
        collection = self.ensure_collection(collection_name)
        include = include or ["documents", "metadatas", "distances"]
        
        try:
            # Run in thread pool to avoid blocking
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.query(
                    query_texts=query_texts,
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=include
                )
            )
            
            logger.debug(f"Query returned {len(results.get('ids', [[]])[0])} results")
            return results
            
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
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        collection = self.ensure_collection(collection_name)
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.update(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
            )
            logger.info(f"Updated {len(ids)} documents")
            
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
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        if not ids and not where:
            raise ValueError("Either ids or where condition must be provided")
        
        collection = self.ensure_collection(collection_name)
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.delete(ids=ids, where=where)
            )
            logger.info(f"Deleted documents: ids={ids}, where={where}")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise
    
    async def get_collection_info(self, collection_name: str = None) -> Dict[str, Any]:
        """Get information about a collection."""
        if not self._client:
            raise RuntimeError("ChromaDB client not connected. Call connect() first.")
        
        collection = self.ensure_collection(collection_name)
        
        try:
            count = await asyncio.get_event_loop().run_in_executor(
                None, collection.count
            )
            
            return {
                "name": collection.name,
                "count": count,
                "metadata": collection.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e)}
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self._embedder:
            raise RuntimeError("Embedder not initialized. Call connect() first.")
        
        return self._embedder([text])[0]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self._embedder:
            raise RuntimeError("Embedder not initialized. Call connect() first.")
        
        return self._embedder(texts)


# Global ChromaDB client instance
_chromadb_client: Optional[ChromaDBClient] = None

async def get_chromadb_client() -> ChromaDBClient:
    """Get or create the global ChromaDB client instance."""
    global _chromadb_client
    
    if _chromadb_client is None:
        _chromadb_client = ChromaDBClient()
        _chromadb_client.connect()
    
    return _chromadb_client

def close_chromadb_client() -> None:
    """Close the global ChromaDB client."""
    global _chromadb_client
    _chromadb_client = None


# Backward compatibility functions
def _connect():
    """Legacy connection function for backward compatibility."""
    global _chromadb_client
    if _chromadb_client is None:
        _chromadb_client = ChromaDBClient()
        _chromadb_client.connect()
    return _chromadb_client._client


def embed(text: str) -> List[float]:
    """Legacy embed function for backward compatibility."""
    client = get_chromadb_client()
    return client.embed_text(text)


def search(query_embedding: List[float], top_k: int) -> List[str]:
    """Legacy search function for backward compatibility."""
    client = _connect()
    collection = client.get_or_create_collection("documents")
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return [m.get("content", "") for m in results.get("metadatas", [{}])[0]]
