"""Client for the ChromaDB vector database."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception:  # pragma: no cover - dependency optional
    chromadb = None

LOGGER = logging.getLogger(__name__)
DB_PATH = Path(__file__).resolve().parents[1] / "database"

_client = None
_embedder = None


def _connect():
    global _client, _embedder
    if _client is None:
        if chromadb is None:
            raise RuntimeError("chromadb package not installed")
        _client = chromadb.PersistentClient(path=str(DB_PATH))
        _embedder = embedding_functions.SentenceTransformerEmbeddingFunction()
    return _client


def embed(text: str) -> List[float]:
    _connect()
    return _embedder(text)


def search(query_embedding: List[float], top_k: int) -> List[str]:
    client = _connect()
    collection = client.get_or_create_collection("documents")
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return [m.get("content", "") for m in results.get("metadatas", [{}])[0]]
