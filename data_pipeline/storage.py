from typing import List, Dict, Any
from pathlib import Path
import logging

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception:  # pragma: no cover
    chromadb = None

LOGGER = logging.getLogger(__name__)
DB_PATH = Path(__file__).resolve().parent / "database"


def _client():
    if chromadb is None:
        raise RuntimeError("chromadb package not installed")
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client


def insert(vectors: List[List[float]], metadatas: List[Dict[str, Any]]):
    client = _client()
    collection = client.get_or_create_collection("documents")
    ids = [str(i) for i in range(collection.count(), collection.count() + len(vectors))]
    collection.add(ids=ids, embeddings=vectors, metadatas=metadatas)
    LOGGER.info("Inserted %d vectors", len(vectors))
