#!/usr/bin/env python3
"""Test script for Base Retrieval Interface functionality."""
import sys
import logging
from pathlib import Path
from datetime import datetime
import asyncio

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all classes can be imported."""
    try:
        from services.retrieval import BaseRetriever, RetrievalResult, RetrievalFilter
        from services.retrieval.base import ResultType, FilterOperator
        
        logger.info("✅ All imports successful")
        assert BaseRetriever is not None
        assert RetrievalResult is not None
        assert RetrievalFilter is not None
        assert ResultType is not None
        assert FilterOperator is not None
        logger.info("✅ All classes imported correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False


def test_enums():
    """Test enum definitions."""
    try:
        from services.retrieval.base import ResultType, FilterOperator
        
        # Test ResultType enum
        assert ResultType.CHUNK.value == "chunk"
        assert ResultType.ENTITY.value == "entity"
        assert ResultType.RELATIONSHIP.value == "relationship"
        assert ResultType.DOCUMENT.value == "document"
        assert ResultType.MIXED.value == "mixed"
        logger.info("✅ ResultType enum values correct")
        
        # Test FilterOperator enum
        assert FilterOperator.EQUALS.value == "equals"
        assert FilterOperator.CONTAINS.value == "contains"
        assert FilterOperator.GREATER_THAN.value == "gt"
        assert FilterOperator.EXISTS.value == "exists"
        logger.info("✅ FilterOperator enum values correct")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enum test failed: {e}")
        return False


def test_retrieval_filter():
    """Test RetrievalFilter dataclass."""
    try:
        from services.retrieval import RetrievalFilter
        from services.retrieval.base import FilterOperator
        
        # Create a filter
        filter = RetrievalFilter(
            field="metadata.user_id",
            operator=FilterOperator.EQUALS,
            value="test_user_123"
        )
        
        assert filter.field == "metadata.user_id"
        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == "test_user_123"
        logger.info("✅ RetrievalFilter creation successful")
        
        # Test to_dict method
        filter_dict = filter.to_dict()
        assert filter_dict["field"] == "metadata.user_id"
        assert filter_dict["operator"] == "equals"
        assert filter_dict["value"] == "test_user_123"
        logger.info("✅ RetrievalFilter to_dict method works")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ RetrievalFilter test failed: {e}")
        return False


def test_retrieval_result():
    """Test RetrievalResult dataclass."""
    try:
        from services.retrieval import RetrievalResult
        from services.retrieval.base import ResultType
        
        # Create a result
        result = RetrievalResult(
            id="test_id_123",
            type=ResultType.CHUNK,
            content="This is test content.",
            metadata={"audio_id": "audio_123", "chunk_index": 0},
            score=0.95,
            source="chromadb",
            entities=[{"text": "John", "type": "PERSON"}],
            relationships=[{"type": "MENTIONS", "target": "entity_456"}]
        )
        
        assert result.id == "test_id_123"
        assert result.type == ResultType.CHUNK
        assert result.content == "This is test content."
        assert result.score == 0.95
        logger.info("✅ RetrievalResult creation successful")
        
        # Test to_dict method
        result_dict = result.to_dict()
        assert result_dict["id"] == "test_id_123"
        assert result_dict["type"] == "chunk"
        assert "timestamp" in result_dict
        assert result_dict["has_embeddings"] == False
        logger.info("✅ RetrievalResult to_dict method works")
        
        # Test merge_with method
        other_result = RetrievalResult(
            id="test_id_123",
            type=ResultType.CHUNK,
            content="This is test content.",
            metadata={"language": "en"},
            score=0.85,
            source="neo4j"
        )
        
        merged = result.merge_with(other_result)
        assert merged.id == "test_id_123"
        assert merged.score == 0.95  # Higher score
        assert "audio_id" in merged.metadata
        assert "language" in merged.metadata
        assert merged.source == "chromadb,neo4j"
        logger.info("✅ RetrievalResult merge_with method works")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ RetrievalResult test failed: {e}")
        return False


def test_base_retriever_structure():
    """Test BaseRetriever abstract class structure."""
    try:
        from services.retrieval import BaseRetriever
        from abc import ABC
        import inspect
        
        # Test that BaseRetriever is abstract
        assert issubclass(BaseRetriever, ABC)
        logger.info("✅ BaseRetriever is an abstract base class")
        
        # Test required abstract methods exist
        abstract_methods = ['initialize', 'search', 'get_by_id']
        for method_name in abstract_methods:
            assert hasattr(BaseRetriever, method_name)
            logger.info(f"✅ Abstract method {method_name} exists")
        
        # Test concrete methods exist
        concrete_methods = ['get_by_ids', 'health_check', 'apply_filters', 
                          'rank_results', 'deduplicate_results', 'format_results']
        for method_name in concrete_methods:
            assert hasattr(BaseRetriever, method_name)
            logger.info(f"✅ Concrete method {method_name} exists")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ BaseRetriever structure test failed: {e}")
        return False


def test_filter_operations():
    """Test filter operation logic."""
    try:
        from services.retrieval import BaseRetriever, RetrievalFilter
        from services.retrieval.base import FilterOperator
        
        # Create a concrete implementation for testing
        class TestRetriever(BaseRetriever):
            async def initialize(self):
                self._initialized = True
            
            async def search(self, query, filters=None, limit=10, **kwargs):
                return []
            
            async def get_by_id(self, id):
                return None
        
        retriever = TestRetriever("test")
        
        # Test filter matching
        test_cases = [
            (5, FilterOperator.EQUALS, 5, True),
            (5, FilterOperator.EQUALS, 10, False),
            ("hello world", FilterOperator.CONTAINS, "world", True),
            ("hello world", FilterOperator.CONTAINS, "foo", False),
            (10, FilterOperator.GREATER_THAN, 5, True),
            (5, FilterOperator.GREATER_THAN, 10, False),
            (2, FilterOperator.IN, [1, 2, 3], True),
            (4, FilterOperator.IN, [1, 2, 3], False),
            (None, FilterOperator.EXISTS, None, False),
            ("value", FilterOperator.EXISTS, None, True),
        ]
        
        for value, operator, filter_value, expected in test_cases:
            result = retriever._match_filter(value, operator, filter_value)
            assert result == expected
            logger.info(f"✅ Filter {operator.value} test passed")
        
        # Test field extraction
        test_item = {
            "id": "123",
            "metadata": {
                "user_id": "user_456",
                "tags": ["tag1", "tag2"]
            }
        }
        
        assert retriever._get_field_value(test_item, "id") == "123"
        assert retriever._get_field_value(test_item, "metadata.user_id") == "user_456"
        assert retriever._get_field_value(test_item, "metadata.tags") == ["tag1", "tag2"]
        assert retriever._get_field_value(test_item, "nonexistent") is None
        logger.info("✅ Field extraction works correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Filter operations test failed: {e}")
        return False


def test_result_processing():
    """Test result processing methods."""
    try:
        from services.retrieval import BaseRetriever, RetrievalResult
        from services.retrieval.base import ResultType
        
        # Create a concrete implementation
        class TestRetriever(BaseRetriever):
            async def initialize(self):
                pass
            
            async def search(self, query, filters=None, limit=10, **kwargs):
                return []
            
            async def get_by_id(self, id):
                return None
        
        retriever = TestRetriever()
        
        # Test ranking
        results = [
            RetrievalResult("1", ResultType.CHUNK, "Content 1", score=0.5),
            RetrievalResult("2", ResultType.CHUNK, "Content 2", score=0.9),
            RetrievalResult("3", ResultType.CHUNK, "Content 3", score=0.7),
        ]
        
        ranked = retriever.rank_results(results)
        assert ranked[0].id == "2"  # Highest score
        assert ranked[1].id == "3"
        assert ranked[2].id == "1"  # Lowest score
        logger.info("✅ Result ranking works correctly")
        
        # Test deduplication
        duplicate_results = [
            RetrievalResult("1", ResultType.CHUNK, "Content", metadata={"a": 1}, score=0.5),
            RetrievalResult("2", ResultType.CHUNK, "Content 2", score=0.9),
            RetrievalResult("1", ResultType.CHUNK, "Content", metadata={"b": 2}, score=0.7),
        ]
        
        deduped = retriever.deduplicate_results(duplicate_results)
        assert len(deduped) == 2
        # Find the merged result
        merged = next(r for r in deduped if r.id == "1")
        assert merged.score == 0.7  # Higher score
        assert "a" in merged.metadata and "b" in merged.metadata
        logger.info("✅ Result deduplication and merging works")
        
        # Test formatting
        format_results = [
            RetrievalResult("1", ResultType.CHUNK, "Content 1"),
            RetrievalResult("2", ResultType.CHUNK, "Content 2"),
        ]
        
        dict_format = retriever.format_results(format_results, "dict")
        assert len(dict_format) == 2
        assert isinstance(dict_format[0], dict)
        
        text_format = retriever.format_results(format_results, "text")
        assert len(text_format) == 2
        assert text_format[0] == "Content 1"
        logger.info("✅ Result formatting works correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Result processing test failed: {e}")
        return False


def test_task_15_requirements():
    """Test that Task 15 specific requirements are met."""
    try:
        from services.retrieval import BaseRetriever, RetrievalResult, RetrievalFilter
        import inspect
        
        # Verify the abstract interface
        assert hasattr(BaseRetriever, 'search')
        assert hasattr(BaseRetriever, 'get_by_id')
        
        # Check method signatures
        search_sig = inspect.signature(BaseRetriever.search)
        assert 'query' in search_sig.parameters
        assert 'filters' in search_sig.parameters
        assert 'limit' in search_sig.parameters
        logger.info("✅ search method has required parameters")
        
        get_by_id_sig = inspect.signature(BaseRetriever.get_by_id)
        assert 'id' in get_by_id_sig.parameters
        logger.info("✅ get_by_id method has required parameters")
        
        # Verify common result format
        result = RetrievalResult(
            id="test",
            type="chunk",  # Can use string
            content="Test content"
        )
        assert hasattr(result, 'id')
        assert hasattr(result, 'type')
        assert hasattr(result, 'content')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'score')
        logger.info("✅ Common result format defined")
        
        # Verify it can be subclassed
        class TestImplementation(BaseRetriever):
            async def initialize(self):
                pass
            
            async def search(self, query, filters=None, limit=10, **kwargs):
                return []
            
            async def get_by_id(self, id):
                return None
        
        impl = TestImplementation()
        assert isinstance(impl, BaseRetriever)
        logger.info("✅ BaseRetriever can be subclassed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Task 15 requirements test failed: {e}")
        return False


async def test_async_methods():
    """Test async method behavior."""
    try:
        from services.retrieval import BaseRetriever, RetrievalResult
        from services.retrieval.base import ResultType
        
        # Create implementation
        class TestRetriever(BaseRetriever):
            async def initialize(self):
                self._initialized = True
            
            async def search(self, query, filters=None, limit=10, **kwargs):
                return [
                    RetrievalResult("1", ResultType.CHUNK, f"Result for: {query}")
                ]
            
            async def get_by_id(self, id):
                if id == "test":
                    return RetrievalResult(id, ResultType.CHUNK, "Test content")
                return None
        
        retriever = TestRetriever()
        
        # Test initialization
        await retriever.initialize()
        assert retriever._initialized
        logger.info("✅ Async initialize works")
        
        # Test search
        results = await retriever.search("test query")
        assert len(results) == 1
        assert results[0].content == "Result for: test query"
        logger.info("✅ Async search works")
        
        # Test get_by_id
        result = await retriever.get_by_id("test")
        assert result is not None
        assert result.id == "test"
        logger.info("✅ Async get_by_id works")
        
        # Test get_by_ids
        results = await retriever.get_by_ids(["test", "nonexistent"])
        assert len(results) == 1
        assert results[0].id == "test"
        logger.info("✅ Async get_by_ids works")
        
        # Test health check
        health = await retriever.health_check()
        assert health["initialized"] == True
        assert health["status"] == "healthy"
        logger.info("✅ Async health_check works")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Async methods test failed: {e}")
        return False


def main():
    """Run all Base Retrieval Interface tests."""
    logger.info("🧪 Running Base Retrieval Interface Tests")
    logger.info("📝 Note: These tests validate implementation structure for Task 15")
    
    # Synchronous tests
    sync_tests = [
        ("Imports", test_imports),
        ("Enums", test_enums),
        ("RetrievalFilter", test_retrieval_filter),
        ("RetrievalResult", test_retrieval_result),
        ("BaseRetriever Structure", test_base_retriever_structure),
        ("Filter Operations", test_filter_operations),
        ("Result Processing", test_result_processing),
        ("Task 15 Requirements", test_task_15_requirements),
    ]
    
    passed = 0
    total = len(sync_tests) + 1  # +1 for async test
    
    for test_name, test_func in sync_tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            result = test_func()
            
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    # Run async test
    logger.info(f"\n--- Running Async Methods ---")
    try:
        result = asyncio.run(test_async_methods())
        if result:
            passed += 1
            logger.info(f"✅ Async Methods PASSED")
        else:
            logger.error(f"❌ Async Methods FAILED")
    except Exception as e:
        logger.error(f"❌ Async Methods FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Base Retrieval Interface tests passed!")
        logger.info("\n📋 Implementation Features Validated:")
        logger.info("  ✅ Abstract base class with required interface")
        logger.info("  ✅ Common result format (RetrievalResult)")
        logger.info("  ✅ Filter criteria support (RetrievalFilter)")
        logger.info("  ✅ Comprehensive filter operations")
        logger.info("  ✅ Result ranking and deduplication")
        logger.info("  ✅ Multiple output format support")
        logger.info("  ✅ Async/await pattern throughout")
        logger.info("  ✅ Health check capability")
        logger.info("  ✅ Field extraction with dot notation")
        logger.info("\n🎯 Task 15 Requirements Met:")
        logger.info("  📦 Common interface for retrieval services")
        logger.info("  🏗️  Abstract base class implementation")
        logger.info("  📊 Standardized result format")
        logger.info("  🔍 Query, filter, and limit support")
        logger.info("  ⚡ Ready for ChromaDB and Neo4j implementations")
        return 0
    else:
        logger.error("💥 Some Base Retrieval Interface tests failed.")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")
        sys.exit(1)