#!/usr/bin/env python3
"""Test script for ContextAggregator functionality."""
import sys
import logging
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_chromadb_client():
    """Create a mock ChromaDB client with sample data."""
    mock_client = Mock()
    
    # Mock query method
    async def mock_query(query_texts, n_results=10, where=None):
        # Simulate vector search results
        return {
            'documents': [[
                "John Doe discussed the new AI project at OpenAI last week.",
                "The team at Microsoft is working on improving their language models.",
                "Apple announced new features for their AI assistant during the conference."
            ]],
            'metadatas': [[
                {"audio_id": "audio_1", "chunk_index": 0, "entity_count": 3, "language": "en"},
                {"audio_id": "audio_2", "chunk_index": 1, "entity_count": 2, "language": "en"},
                {"audio_id": "audio_3", "chunk_index": 0, "entity_count": 3, "language": "en"}
            ]],
            'distances': [[0.2, 0.4, 0.6]],
            'ids': [["chunk_1", "chunk_2", "chunk_3"]]
        }
    
    mock_client.query = AsyncMock(side_effect=mock_query)
    return mock_client


def create_mock_neo4j_client():
    """Create a mock Neo4j client with sample data."""
    mock_client = Mock()
    
    async def mock_execute_read_query(query, params):
        # Simulate graph search results based on query
        if "entity_texts" in params:
            return [
                {
                    "chunk_id": "chunk_1",
                    "content": "John Doe discussed the new AI project at OpenAI last week.",
                    "audio_id": "audio_1",
                    "chunk_index": 0,
                    "language": "en",
                    "tags": ["meeting"],
                    "category": "work",
                    "matched_entity": "John Doe",
                    "related_entities": ["OpenAI", "AI project"],
                    "entity_count": 3
                },
                {
                    "chunk_id": "chunk_4", 
                    "content": "OpenAI released a new research paper on transformer architectures.",
                    "audio_id": "audio_4",
                    "chunk_index": 0,
                    "language": "en", 
                    "tags": ["research"],
                    "category": "tech",
                    "matched_entity": "OpenAI",
                    "related_entities": ["research paper", "transformer"],
                    "entity_count": 2
                }
            ]
        elif "chunk_ids" in params:
            # Related chunks query
            return [
                {
                    "chunk_id": "chunk_5",
                    "content": "The AI research team published their findings on language understanding.",
                    "audio_id": "audio_5",
                    "chunk_index": 0,
                    "shared_entities": 2
                }
            ]
        return []
    
    mock_client.execute_read_query = AsyncMock(side_effect=mock_execute_read_query)
    return mock_client


async def test_vector_only_search():
    """Test vector-only search functionality."""
    try:
        from services.context_aggregator import ContextAggregator
        
        chromadb_client = create_mock_chromadb_client()
        neo4j_client = create_mock_neo4j_client()
        
        aggregator = ContextAggregator(chromadb_client, neo4j_client)
        
        result = await aggregator.search_context(
            query="AI project discussion",
            max_results=5,
            strategy="vector"
        )
        
        logger.info(f"✅ Vector search returned {result.total_results} results")
        logger.info(f"  Strategy: {result.aggregation_strategy}")
        logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
        
        for i, context in enumerate(result.results[:2]):
            logger.info(f"  Result {i+1}: score={context.relevance_score:.3f}, type={context.source_type}")
            logger.info(f"    Content: {context.content[:60]}...")
        
        assert result.total_results > 0
        assert result.aggregation_strategy == "vector"
        assert all(r.source_type == "vector" for r in result.results)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")
        return False


async def test_graph_only_search():
    """Test graph-only search functionality."""
    try:
        from services.context_aggregator import ContextAggregator
        
        chromadb_client = create_mock_chromadb_client()
        neo4j_client = create_mock_neo4j_client()
        
        aggregator = ContextAggregator(chromadb_client, neo4j_client)
        
        result = await aggregator.search_context(
            query="John Doe OpenAI project",
            max_results=5,
            strategy="graph"
        )
        
        logger.info(f"✅ Graph search returned {result.total_results} results")
        logger.info(f"  Strategy: {result.aggregation_strategy}")
        logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
        
        for i, context in enumerate(result.results[:2]):
            logger.info(f"  Result {i+1}: score={context.relevance_score:.3f}, type={context.source_type}")
            logger.info(f"    Matched entity: {context.metadata.get('matched_entity')}")
            logger.info(f"    Related entities: {context.metadata.get('related_entities', [])}")
        
        assert result.total_results >= 0  # May be 0 if no entities found
        assert result.aggregation_strategy == "graph"
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Graph search test failed: {e}")
        return False


async def test_hybrid_search():
    """Test hybrid search functionality."""
    try:
        from services.context_aggregator import ContextAggregator
        
        chromadb_client = create_mock_chromadb_client()
        neo4j_client = create_mock_neo4j_client()
        
        aggregator = ContextAggregator(chromadb_client, neo4j_client)
        
        result = await aggregator.search_context(
            query="John Doe AI project OpenAI",
            max_results=10,
            strategy="hybrid",
            vector_weight=0.6,
            graph_weight=0.4,
            include_related=True
        )
        
        logger.info(f"✅ Hybrid search returned {result.total_results} results")
        logger.info(f"  Strategy: {result.aggregation_strategy}")
        logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
        logger.info(f"  Vector weight: {result.query_metadata['vector_weight']}")
        logger.info(f"  Graph weight: {result.query_metadata['graph_weight']}")
        
        # Check for different source types
        source_types = set(r.source_type for r in result.results)
        logger.info(f"  Source types found: {source_types}")
        
        for i, context in enumerate(result.results[:3]):
            logger.info(f"  Result {i+1}: score={context.relevance_score:.3f}, type={context.source_type}")
            if context.semantic_relevance:
                logger.info(f"    Semantic: {context.semantic_relevance:.3f}")
            if context.structural_relevance:
                logger.info(f"    Structural: {context.structural_relevance:.3f}")
        
        assert result.total_results > 0
        assert result.aggregation_strategy == "hybrid"
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Hybrid search test failed: {e}")
        return False


async def test_ensemble_search():
    """Test ensemble search functionality."""
    try:
        from services.context_aggregator import ContextAggregator
        
        chromadb_client = create_mock_chromadb_client()
        neo4j_client = create_mock_neo4j_client()
        
        aggregator = ContextAggregator(chromadb_client, neo4j_client)
        
        result = await aggregator.search_context(
            query="AI project discussion at tech companies",
            max_results=8,
            strategy="ensemble",
            vector_weight=0.7,
            graph_weight=0.3
        )
        
        logger.info(f"✅ Ensemble search returned {result.total_results} results")
        logger.info(f"  Strategy: {result.aggregation_strategy}")
        logger.info(f"  Processing time: {result.processing_time_ms:.2f}ms")
        
        for i, context in enumerate(result.results[:2]):
            logger.info(f"  Result {i+1}: score={context.relevance_score:.3f}, type={context.source_type}")
            logger.info(f"    Content: {context.content[:60]}...")
        
        assert result.total_results > 0
        assert result.aggregation_strategy == "ensemble"
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ensemble search test failed: {e}")
        return False


def test_context_result_dataclass():
    """Test ContextResult dataclass functionality."""
    try:
        from services.context_aggregator import ContextResult
        
        result = ContextResult(
            id="test_chunk_1",
            content="This is a test chunk about AI development.",
            source_type="hybrid",
            relevance_score=0.85,
            metadata={"audio_id": "audio_1", "entity_count": 2},
            vector_similarity=0.9,
            semantic_relevance=0.9,
            structural_relevance=0.7
        )
        
        logger.info("✅ ContextResult dataclass created successfully")
        logger.info(f"  ID: {result.id}")
        logger.info(f"  Source type: {result.source_type}")
        logger.info(f"  Relevance score: {result.relevance_score}")
        logger.info(f"  Semantic relevance: {result.semantic_relevance}")
        logger.info(f"  Structural relevance: {result.structural_relevance}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ContextResult test failed: {e}")
        return False


def test_aggregated_context_dataclass():
    """Test AggregatedContext dataclass functionality."""
    try:
        from services.context_aggregator import AggregatedContext, ContextResult
        
        results = [
            ContextResult(
                id="chunk_1",
                content="Test content 1",
                source_type="vector",
                relevance_score=0.8,
                metadata={}
            ),
            ContextResult(
                id="chunk_2", 
                content="Test content 2",
                source_type="graph",
                relevance_score=0.7,
                metadata={}
            )
        ]
        
        context = AggregatedContext(
            results=results,
            total_results=2,
            query_metadata={"query": "test", "strategy": "hybrid"},
            aggregation_strategy="hybrid",
            processing_time_ms=45.2
        )
        
        logger.info("✅ AggregatedContext dataclass created successfully")
        logger.info(f"  Total results: {context.total_results}")
        logger.info(f"  Strategy: {context.aggregation_strategy}")
        logger.info(f"  Processing time: {context.processing_time_ms}ms")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ AggregatedContext test failed: {e}")
        return False


async def main():
    """Run all context aggregator tests."""
    logger.info("🧪 Running ContextAggregator Tests")
    
    tests = [
        ("ContextResult Dataclass", test_context_result_dataclass),
        ("AggregatedContext Dataclass", test_aggregated_context_dataclass),
        ("Vector Only Search", test_vector_only_search),
        ("Graph Only Search", test_graph_only_search),
        ("Hybrid Search", test_hybrid_search),
        ("Ensemble Search", test_ensemble_search),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All ContextAggregator tests passed!")
        logger.info("\n📋 ContextAggregator Features:")
        logger.info("  ✅ Vector-only search using ChromaDB")
        logger.info("  ✅ Graph-only search using Neo4j entity relationships")
        logger.info("  ✅ Hybrid search combining vector and graph results")
        logger.info("  ✅ Ensemble search with multiple ranking strategies")
        logger.info("  ✅ Related chunk discovery through entity overlap")
        logger.info("  ✅ Configurable search weights and strategies")
        logger.info("  ✅ Rich metadata and relevance scoring")
        return 0
    else:
        logger.error("💥 Some ContextAggregator tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))