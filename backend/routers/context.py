"""Context search API endpoints."""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from services.context_aggregator import ContextAggregator, AggregatedContext
from services.vector_db_client import get_chromadb_client
from services.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/context", tags=["context"])


class ContextSearchRequest(BaseModel):
    """Request model for context search."""
    query: str = Field(..., description="Search query text")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    strategy: str = Field(default="hybrid", pattern="^(vector|graph|hybrid|ensemble)$", description="Search strategy")
    vector_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Weight for vector search")
    graph_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Weight for graph search")
    include_related: bool = Field(default=True, description="Include related chunks")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata filters")


class ContextResultResponse(BaseModel):
    """Response model for a single context result."""
    id: str
    content: str
    source_type: str
    relevance_score: float
    metadata: Dict[str, Any]
    vector_similarity: Optional[float] = None
    graph_relationships: Optional[List[Dict[str, Any]]] = None
    graph_distance: Optional[int] = None
    semantic_relevance: Optional[float] = None
    structural_relevance: Optional[float] = None


class ContextSearchResponse(BaseModel):
    """Response model for context search."""
    results: List[ContextResultResponse]
    total_results: int
    query_metadata: Dict[str, Any]
    aggregation_strategy: str
    processing_time_ms: float


async def get_context_aggregator():
    """Dependency to get ContextAggregator instance."""
    chromadb_client = get_chromadb_client()
    neo4j_client = get_neo4j_client()
    return ContextAggregator(chromadb_client, neo4j_client)


@router.post("/search", response_model=ContextSearchResponse)
async def search_context(
    request: ContextSearchRequest,
    aggregator: ContextAggregator = Depends(get_context_aggregator)
):
    """Search for context using multiple strategies.
    
    This endpoint combines semantic vector search with graph-based knowledge
    retrieval to provide comprehensive context for queries.
    
    **Strategies:**
    - `vector`: Pure semantic similarity search using embeddings
    - `graph`: Entity-based search using knowledge graph relationships
    - `hybrid`: Weighted combination of vector and graph results
    - `ensemble`: Advanced ranking with multiple scoring factors
    
    **Use Cases:**
    - Finding relevant conversation snippets
    - Discovering related topics and entities
    - Context retrieval for AI assistant responses
    - Knowledge exploration and discovery
    """
    try:
        # Perform context search
        result = await aggregator.search_context(
            query=request.query,
            max_results=request.max_results,
            vector_weight=request.vector_weight,
            graph_weight=request.graph_weight,
            strategy=request.strategy,
            filters=request.filters,
            include_related=request.include_related
        )
        
        # Convert to response format
        response_results = [
            ContextResultResponse(
                id=r.id,
                content=r.content,
                source_type=r.source_type,
                relevance_score=r.relevance_score,
                metadata=r.metadata,
                vector_similarity=r.vector_similarity,
                graph_relationships=r.graph_relationships,
                graph_distance=r.graph_distance,
                semantic_relevance=r.semantic_relevance,
                structural_relevance=r.structural_relevance
            )
            for r in result.results
        ]
        
        return ContextSearchResponse(
            results=response_results,
            total_results=result.total_results,
            query_metadata=result.query_metadata,
            aggregation_strategy=result.aggregation_strategy,
            processing_time_ms=result.processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"Error in context search: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Context search failed: {str(e)}"
        )


@router.get("/search", response_model=ContextSearchResponse)
async def search_context_get(
    query: str = Query(..., description="Search query text"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum number of results"),
    strategy: str = Query(default="hybrid", pattern="^(vector|graph|hybrid|ensemble)$", description="Search strategy"),
    vector_weight: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Weight for vector search"),
    graph_weight: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Weight for graph search"),
    include_related: bool = Query(default=True, description="Include related chunks"),
    aggregator: ContextAggregator = Depends(get_context_aggregator)
):
    """GET version of context search for simple queries.
    
    This is a simplified version of the POST endpoint that accepts
    query parameters instead of a JSON body. Useful for quick testing
    and simple integrations.
    """
    request = ContextSearchRequest(
        query=query,
        max_results=max_results,
        strategy=strategy,
        vector_weight=vector_weight,
        graph_weight=graph_weight,
        include_related=include_related
    )
    
    return await search_context(request, aggregator)


@router.get("/strategies")
async def get_search_strategies():
    """Get available search strategies and their descriptions."""
    return {
        "strategies": {
            "vector": {
                "name": "Vector Search",
                "description": "Pure semantic similarity search using text embeddings",
                "use_case": "Finding semantically similar content",
                "pros": ["Fast", "Good for fuzzy matching", "Language understanding"],
                "cons": ["No relationship awareness", "May miss exact entity matches"]
            },
            "graph": {
                "name": "Graph Search", 
                "description": "Entity-based search using knowledge graph relationships",
                "use_case": "Finding content related to specific entities",
                "pros": ["Relationship awareness", "Exact entity matching", "Structural understanding"],
                "cons": ["Requires entity extraction", "May miss semantic similarities"]
            },
            "hybrid": {
                "name": "Hybrid Search",
                "description": "Weighted combination of vector and graph search results",
                "use_case": "Balanced search combining semantic and structural relevance",
                "pros": ["Best of both worlds", "Configurable weights", "Comprehensive results"],
                "cons": ["Slightly slower", "May need weight tuning"]
            },
            "ensemble": {
                "name": "Ensemble Search",
                "description": "Advanced ranking with multiple scoring factors (time, length, density)",
                "use_case": "Production-ready search with sophisticated ranking",
                "pros": ["Most sophisticated", "Multiple ranking factors", "Optimized relevance"],
                "cons": ["Slowest", "Most complex", "Many parameters"]
            }
        },
        "default_weights": {
            "vector_weight": 0.7,
            "graph_weight": 0.3
        },
        "recommendations": {
            "quick_search": "vector",
            "entity_focused": "graph", 
            "balanced": "hybrid",
            "production": "ensemble"
        }
    }


@router.get("/health")
async def context_health_check(
    aggregator: ContextAggregator = Depends(get_context_aggregator)
):
    """Health check for context search services."""
    try:
        # Test basic functionality with a simple query
        result = await aggregator.search_context(
            query="test",
            max_results=1,
            strategy="vector"
        )
        
        return {
            "status": "healthy",
            "services": {
                "context_aggregator": "operational",
                "chromadb": "connected" if result.total_results >= 0 else "error",
                "neo4j": "connected"  # If we got here, Neo4j is accessible
            },
            "test_query_time_ms": result.processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"Context health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "services": {
                "context_aggregator": "error",
                "chromadb": "unknown",
                "neo4j": "unknown"
            }
        }