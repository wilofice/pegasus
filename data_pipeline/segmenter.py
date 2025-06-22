from typing import List
import nltk
import logging

LOGGER = logging.getLogger(__name__)

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:  # pragma: no cover - ensure tokenizers are present
    nltk.download('punkt')


def chunk_text(text: str, size: int = 150) -> List[str]:
    """Split text into chunks of roughly *size* words."""
    sentences = nltk.tokenize.sent_tokenize(text)
    chunks = []
    current = []
    count = 0
    for sent in sentences:
        words = sent.split()
        if count + len(words) > size and current:
            chunks.append(" ".join(current))
            current = []
            count = 0
        current.extend(words)
        count += len(words)
    if current:
        chunks.append(" ".join(current))
    LOGGER.info("Segmented text into %d chunks", len(chunks))
    return chunks
