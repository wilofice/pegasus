"""Text chunking service with overlap strategy."""
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with position information."""
    text: str
    start: int
    end: int
    chunk_index: int


class ChunkingService:
    """Service for chunking text with configurable overlap."""
    
    def __init__(
        self, 
        chunk_size: int = 1000,
        overlap_size: int = 200,
        min_chunk_size: int = 100
    ):
        """Initialize chunking service.
        
        Args:
            chunk_size: Target size for each chunk in characters
            overlap_size: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size to avoid tiny fragments
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        if overlap_size >= chunk_size:
            raise ValueError("Overlap size must be less than chunk size")
    
    def chunk_text(self, text: str) -> List[TextChunk]:
        """Chunk text with overlap strategy.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []
        
        text = text.strip()
        if len(text) <= self.chunk_size:
            return [TextChunk(
                text=text,
                start=0,
                end=len(text),
                chunk_index=0
            )]
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # Try to find a good break point (sentence boundary)
            if end < len(text):
                end = self._find_sentence_boundary(text, start, end)
            
            # Extract chunk text
            chunk_text = text[start:end].strip()
            
            # Skip empty chunks
            if chunk_text:
                chunks.append(TextChunk(
                    text=chunk_text,
                    start=start,
                    end=end,
                    chunk_index=chunk_index
                ))
                chunk_index += 1
            
            # Calculate next start position with overlap
            if end >= len(text):
                break
                
            # Move start position considering overlap
            next_start = end - self.overlap_size
            
            # Ensure we make progress
            if next_start <= start:
                next_start = start + 1
            
            start = next_start
        
        # Merge small trailing chunks
        chunks = self._merge_small_chunks(chunks)
        
        logger.info(f"Chunked text into {len(chunks)} chunks (avg size: {sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0} chars)")
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """Find a good sentence boundary near the preferred end position.
        
        Args:
            text: Full text
            start: Start position of current chunk
            preferred_end: Preferred end position
            
        Returns:
            Adjusted end position at sentence boundary
        """
        # Look for sentence endings in a window around preferred_end
        search_window = min(100, preferred_end - start)
        search_start = max(start, preferred_end - search_window)
        search_end = min(len(text), preferred_end + search_window // 2)
        
        # Sentence boundary patterns (in order of preference)
        boundaries = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        
        best_pos = preferred_end
        best_score = 0
        
        for boundary in boundaries:
            pos = text.rfind(boundary, search_start, search_end)
            if pos != -1:
                # Position after the boundary
                boundary_end = pos + len(boundary)
                
                # Score based on proximity to preferred position
                distance = abs(boundary_end - preferred_end)
                score = search_window - distance
                
                if score > best_score:
                    best_score = score
                    best_pos = boundary_end
        
        # Ensure minimum chunk size
        if best_pos - start < self.min_chunk_size:
            return preferred_end
        
        return best_pos
    
    def _merge_small_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Merge chunks that are too small with adjacent chunks.
        
        Args:
            chunks: List of chunks to process
            
        Returns:
            List of chunks with small ones merged
        """
        if not chunks:
            return chunks
        
        merged = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            
            # If chunk is too small and not the last one, try to merge with next
            if (len(current_chunk.text) < self.min_chunk_size and 
                i < len(chunks) - 1):
                
                next_chunk = chunks[i + 1]
                
                # Merge with next chunk
                merged_text = current_chunk.text + " " + next_chunk.text
                merged_chunk = TextChunk(
                    text=merged_text.strip(),
                    start=current_chunk.start,
                    end=next_chunk.end,
                    chunk_index=current_chunk.chunk_index
                )
                
                merged.append(merged_chunk)
                i += 2  # Skip the next chunk as it's been merged
            else:
                merged.append(current_chunk)
                i += 1
        
        # Update chunk indices
        for idx, chunk in enumerate(merged):
            chunk.chunk_index = idx
        
        return merged
    
    def get_chunk_stats(self, chunks: List[TextChunk]) -> dict:
        """Get statistics about the chunks.
        
        Args:
            chunks: List of chunks to analyze
            
        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
        
        chunk_sizes = [len(chunk.text) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(chunk_sizes),
            "avg_chunk_size": sum(chunk_sizes) // len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "overlap_efficiency": self._calculate_overlap_efficiency(chunks)
        }
    
    def _calculate_overlap_efficiency(self, chunks: List[TextChunk]) -> float:
        """Calculate overlap efficiency (how much overlap vs total text).
        
        Args:
            chunks: List of chunks
            
        Returns:
            Overlap efficiency as percentage
        """
        if len(chunks) <= 1:
            return 0.0
        
        total_overlap = 0
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # Calculate actual overlap
            overlap_start = max(prev_chunk.start, curr_chunk.start)
            overlap_end = min(prev_chunk.end, curr_chunk.end)
            
            if overlap_end > overlap_start:
                total_overlap += overlap_end - overlap_start
        
        total_text = sum(len(chunk.text) for chunk in chunks)
        return (total_overlap / total_text) * 100 if total_text > 0 else 0.0