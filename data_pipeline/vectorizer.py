from typing import List
import logging

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

LOGGER = logging.getLogger(__name__)
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _load_model():
    global _model
    if _model is None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers package not installed")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(chunks: List[str]) -> List[List[float]]:
    """Embed a list of text chunks into vectors."""
    model = _load_model()
    vectors = model.encode(chunks, show_progress_bar=False).tolist()
    LOGGER.info("Vectorized %d chunks", len(vectors))
    return vectors
