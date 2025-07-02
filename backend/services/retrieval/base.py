"""Base retrieval interface for Pegasus Brain retrieval services."""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """Types of retrieval results."""
    CHUNK = "chunk"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    DOCUMENT = "document"
    MIXED = "mixed"


class FilterOperator(Enum):
    """Filter operators for retrieval queries."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


@dataclass
class RetrievalFilter:
    """Filter criteria for retrieval queries."""
    field: str
    operator: FilterOperator
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary representation."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value
        }


@dataclass
class RetrievalResult:
    """Standardized result format for all retrievers."""
    id: str
    type: ResultType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 1.0
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Optional fields for specific result types
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "entities": self.entities,
            "relationships": self.relationships,
            "has_embeddings": len(self.embeddings) > 0
        }
    
    def merge_with(self, other: 'RetrievalResult') -> 'RetrievalResult':
        """Merge this result with another result."""
        if self.id != other.id:
            raise ValueError("Cannot merge results with different IDs")
        
        # Merge metadata
        merged_metadata = {**self.metadata, **other.metadata}
        
        # Merge entities and relationships
        merged_entities = self.entities + [e for e in other.entities if e not in self.entities]
        merged_relationships = self.relationships + [r for r in other.relationships if r not in self.relationships]
        
        # Use higher score
        merged_score = max(self.score, other.score)
        
        return RetrievalResult(
            id=self.id,
            type=ResultType.MIXED if self.type != other.type else self.type,
            content=self.content,
            metadata=merged_metadata,
            score=merged_score,
            source=f"{self.source},{other.source}",
            timestamp=min(self.timestamp, other.timestamp),
            entities=merged_entities,
            relationships=merged_relationships,
            embeddings=self.embeddings or other.embeddings
        )


class BaseRetriever(ABC):
    """Abstract base class for all retrieval services."""
    
    def __init__(self, name: str = None):
        """Initialize the base retriever.
        
        Args:
            name: Optional name for the retriever
        """
        self.name = name or self.__class__.__name__
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the retriever and its connections."""
        pass
    
    @abstractmethod
    async def search(self, 
                    query: str, 
                    filters: List[RetrievalFilter] = None,
                    limit: int = 10,
                    **kwargs) -> List[RetrievalResult]:
        """Search for relevant content.
        
        Args:
            query: Search query text
            filters: Optional list of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional retriever-specific parameters
            
        Returns:
            List of retrieval results
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[RetrievalResult]:
        """Retrieve a specific item by ID.
        
        Args:
            id: Unique identifier of the item
            
        Returns:
            RetrievalResult if found, None otherwise
        """
        pass
    
    async def get_by_ids(self, ids: List[str]) -> List[RetrievalResult]:
        """Retrieve multiple items by their IDs.
        
        Args:
            ids: List of unique identifiers
            
        Returns:
            List of found results
        """
        results = []
        for id in ids:
            result = await self.get_by_id(id)
            if result:
                results.append(result)
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the retriever.
        
        Returns:
            Dictionary with health status information
        """
        return {
            "retriever": self.name,
            "initialized": self._initialized,
            "status": "healthy" if self._initialized else "not_initialized",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def apply_filters(self, items: List[Any], filters: List[RetrievalFilter]) -> List[Any]:
        """Apply filters to a list of items.
        
        Args:
            items: List of items to filter
            filters: List of filters to apply
            
        Returns:
            Filtered list of items
        """
        if not filters:
            return items
        
        filtered = items
        for filter in filters:
            filtered = self._apply_single_filter(filtered, filter)
        
        return filtered
    
    def _apply_single_filter(self, items: List[Any], filter: RetrievalFilter) -> List[Any]:
        """Apply a single filter to items.
        
        Args:
            items: List of items to filter
            filter: Single filter to apply
            
        Returns:
            Filtered list of items
        """
        filtered = []
        
        for item in items:
            # Extract the field value from the item
            value = self._get_field_value(item, filter.field)
            
            # Apply the filter operator
            if self._match_filter(value, filter.operator, filter.value):
                filtered.append(item)
        
        return filtered
    
    def _get_field_value(self, item: Any, field_path: str) -> Any:
        """Extract a field value from an item using dot notation.
        
        Args:
            item: Item to extract from
            field_path: Dot-separated field path (e.g., "metadata.user_id")
            
        Returns:
            Field value or None if not found
        """
        if isinstance(item, dict):
            parts = field_path.split('.')
            value = item
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value
        elif hasattr(item, field_path):
            return getattr(item, field_path)
        else:
            # Try nested attribute access
            parts = field_path.split('.')
            value = item
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
    
    def _match_filter(self, value: Any, operator: FilterOperator, filter_value: Any) -> bool:
        """Check if a value matches a filter condition.
        
        Args:
            value: Value to check
            operator: Filter operator
            filter_value: Value to compare against
            
        Returns:
            True if the filter matches, False otherwise
        """
        if operator == FilterOperator.EXISTS:
            return value is not None
        elif operator == FilterOperator.NOT_EXISTS:
            return value is None
        
        # For other operators, None values don't match
        if value is None:
            return False
        
        if operator == FilterOperator.EQUALS:
            return value == filter_value
        elif operator == FilterOperator.NOT_EQUALS:
            return value != filter_value
        elif operator == FilterOperator.CONTAINS:
            return filter_value in str(value)
        elif operator == FilterOperator.NOT_CONTAINS:
            return filter_value not in str(value)
        elif operator == FilterOperator.IN:
            return value in filter_value
        elif operator == FilterOperator.NOT_IN:
            return value not in filter_value
        elif operator == FilterOperator.GREATER_THAN:
            return value > filter_value
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return value >= filter_value
        elif operator == FilterOperator.LESS_THAN:
            return value < filter_value
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return value <= filter_value
        else:
            logger.warning(f"Unknown filter operator: {operator}")
            return False
    
    def rank_results(self, results: List[RetrievalResult], query: str = None) -> List[RetrievalResult]:
        """Rank results by relevance.
        
        Args:
            results: List of results to rank
            query: Optional query for relevance scoring
            
        Returns:
            Ranked list of results
        """
        # Default implementation sorts by score
        return sorted(results, key=lambda r: r.score, reverse=True)
    
    def deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicate results and merge metadata.
        
        Args:
            results: List of results that may contain duplicates
            
        Returns:
            Deduplicated list of results
        """
        seen = {}
        deduplicated = []
        
        for result in results:
            if result.id in seen:
                # Merge with existing result
                existing = seen[result.id]
                merged = existing.merge_with(result)
                # Update the result in the deduplicated list
                for i, r in enumerate(deduplicated):
                    if r.id == result.id:
                        deduplicated[i] = merged
                        break
                seen[result.id] = merged
            else:
                seen[result.id] = result
                deduplicated.append(result)
        
        return deduplicated
    
    def format_results(self, results: List[RetrievalResult], format: str = "dict") -> Union[List[Dict], List[str]]:
        """Format results for output.
        
        Args:
            results: List of results to format
            format: Output format ("dict", "text", "json")
            
        Returns:
            Formatted results
        """
        if format == "dict":
            return [r.to_dict() for r in results]
        elif format == "text":
            return [r.content for r in results]
        elif format == "json":
            import json
            return json.dumps([r.to_dict() for r in results], indent=2)
        else:
            logger.warning(f"Unknown format: {format}, using dict")
            return [r.to_dict() for r in results]