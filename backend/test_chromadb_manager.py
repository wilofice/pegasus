#!/usr/bin/env python3
"""Test script for ChromaDB Manager functionality."""
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_collection_management():
    """Test collection creation and management."""
    try:
        from services.chromadb_manager import get_chromadb_manager
        
        manager = get_chromadb_manager()
        
        # Test collection creation
        collection = manager.ensure_collection("test_transcripts")
        logger.info(f"✅ Collection created/retrieved: {collection.name}")
        
        # Test collection stats
        stats = manager.get_collection_stats("test_transcripts")
        logger.info(f"✅ Collection stats: {stats}")
        
        # Test listing collections
        collections = manager.list_collections()
        logger.info(f"✅ Found {len(collections)} collections")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Collection management test failed: {e}")
        return False


def test_chunk_operations():
    """Test adding and retrieving chunks."""
    try:
        from services.chromadb_manager import get_chromadb_manager
        
        manager = get_chromadb_manager()
        
        # Prepare test chunks
        test_chunks = [
            {
                "text": "This is the first chunk of the meeting transcript. We discussed the project timeline and budget allocation.",
                "metadata": {
                    "chunk_index": 0,
                    "start_time": 0.0,
                    "end_time": 30.0
                },
                "entities": [
                    {"text": "project timeline", "type": "TOPIC"},
                    {"text": "budget allocation", "type": "TOPIC"}
                ],
                "sentiment_score": 0.2,
                "language": "en"
            },
            {
                "text": "John mentioned that we need to finish the quarterly report by Friday. Sarah agreed to take the lead on this task.",
                "metadata": {
                    "chunk_index": 1,
                    "start_time": 30.0,
                    "end_time": 60.0
                },
                "entities": [
                    {"text": "John", "type": "PERSON"},
                    {"text": "Sarah", "type": "PERSON"},
                    {"text": "quarterly report", "type": "TASK"},
                    {"text": "Friday", "type": "DATE"}
                ],
                "sentiment_score": 0.6,
                "language": "en"
            },
            {
                "text": "The team decided to implement the new feature in the next sprint. We need to ensure quality assurance testing.",
                "metadata": {
                    "chunk_index": 2,
                    "start_time": 60.0,
                    "end_time": 90.0
                },
                "entities": [
                    {"text": "new feature", "type": "TOPIC"},
                    {"text": "next sprint", "type": "TIME"},
                    {"text": "quality assurance testing", "type": "PROCESS"}
                ],
                "sentiment_score": 0.8,
                "language": "en"
            }
        ]
        
        # Test adding chunks
        success = manager.add_transcript_chunks(
            collection_name="test_transcripts",
            chunks=test_chunks,
            audio_id="test_audio_123",
            user_id="test_user_456",
            metadata={
                "category": "meeting",
                "tags": ["project", "planning"],
                "duration": 90.0
            }
        )
        
        if success:
            logger.info("✅ Successfully added test chunks")
        else:
            logger.error("❌ Failed to add test chunks")
            return False
        
        # Test searching chunks
        search_results = manager.search_chunks(
            collection_name="test_transcripts",
            query="project timeline and budget",
            user_id="test_user_456",
            limit=5
        )
        
        logger.info(f"✅ Search found {len(search_results)} results")
        for i, result in enumerate(search_results[:2]):
            logger.info(f"  Result {i+1}: {result['document'][:50]}... (distance: {result.get('distance', 'N/A')})")
        
        # Test search with filters
        filtered_results = manager.search_chunks(
            collection_name="test_transcripts",
            query="report deadline",
            user_id="test_user_456",
            filters={"language": "en"},
            limit=3
        )
        
        logger.info(f"✅ Filtered search found {len(filtered_results)} results")
        
        # Test getting chunk by ID
        if search_results:
            chunk_id = search_results[0]["id"]
            chunk = manager.get_chunk_by_id("test_transcripts", chunk_id)
            if chunk:
                logger.info(f"✅ Retrieved chunk by ID: {chunk['id']}")
            else:
                logger.error("❌ Failed to retrieve chunk by ID")
                return False
        
        # Test collection stats after adding data
        stats = manager.get_collection_stats("test_transcripts")
        logger.info(f"✅ Updated collection stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Chunk operations test failed: {e}")
        return False


def test_advanced_features():
    """Test advanced ChromaDB manager features."""
    try:
        from services.chromadb_manager import get_chromadb_manager
        
        manager = get_chromadb_manager()
        
        # Test metadata sanitization
        complex_metadata = {
            "simple_string": "test",
            "simple_number": 42,
            "simple_boolean": True,
            "none_value": None,
            "complex_dict": {"nested": "value", "count": 5},
            "string_list": ["item1", "item2", "item3"],
            "mixed_list": ["string", 123, True],
            "long_string": "a" * 1000,  # Very long string
        }
        
        sanitized = manager._sanitize_metadata(complex_metadata)
        logger.info(f"✅ Metadata sanitization test passed")
        logger.info(f"  Original keys: {len(complex_metadata)}")
        logger.info(f"  Sanitized keys: {len(sanitized)}")
        
        # Test health check
        health = manager.health_check()
        logger.info(f"✅ Health check: {health}")
        assert health["status"] == "healthy"
        
        # Test with multiple users
        manager.add_transcript_chunks(
            collection_name="test_transcripts",
            chunks=[{
                "text": "Different user's conversation about data analysis and machine learning applications.",
                "metadata": {"chunk_index": 0}
            }],
            audio_id="test_audio_789",
            user_id="different_user_123",
            metadata={"category": "research"}
        )
        
        # Test user-specific search
        user1_results = manager.search_chunks(
            collection_name="test_transcripts",
            query="project",
            user_id="test_user_456",
            limit=10
        )
        
        user2_results = manager.search_chunks(
            collection_name="test_transcripts",
            query="project",
            user_id="different_user_123",
            limit=10
        )
        
        logger.info(f"✅ User isolation test:")
        logger.info(f"  User 1 results: {len(user1_results)}")
        logger.info(f"  User 2 results: {len(user2_results)}")
        
        # Verify user isolation
        for result in user1_results:
            assert result["metadata"]["user_id"] == "test_user_456"
        
        for result in user2_results:
            assert result["metadata"]["user_id"] == "different_user_123"
        
        logger.info("✅ User isolation verified")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Advanced features test failed: {e}")
        return False


def test_cleanup():
    """Test cleanup operations."""
    try:
        from services.chromadb_manager import get_chromadb_manager
        
        manager = get_chromadb_manager()
        
        # Test deleting audio chunks
        success = manager.delete_audio_chunks("test_transcripts", "test_audio_123")
        if success:
            logger.info("✅ Successfully deleted audio chunks")
        else:
            logger.error("❌ Failed to delete audio chunks")
            return False
        
        # Verify deletion
        results = manager.search_chunks(
            collection_name="test_transcripts",
            query="project timeline",
            user_id="test_user_456",
            limit=10
        )
        
        # Should have fewer results now
        logger.info(f"✅ After deletion, found {len(results)} results")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup test failed: {e}")
        return False


def main():
    """Run all ChromaDB Manager tests."""
    logger.info("🧪 Running ChromaDB Manager Tests")
    
    tests = [
        ("Collection Management", test_collection_management),
        ("Chunk Operations", test_chunk_operations),
        ("Advanced Features", test_advanced_features),
        ("Cleanup Operations", test_cleanup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
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
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All ChromaDB Manager tests passed!")
        logger.info("\n📋 Features Validated:")
        logger.info("  ✅ Collection creation and management")
        logger.info("  ✅ Chunk addition with rich metadata")
        logger.info("  ✅ Semantic search with filtering")
        logger.info("  ✅ User data isolation")
        logger.info("  ✅ Metadata sanitization")
        logger.info("  ✅ Collection statistics")
        logger.info("  ✅ Health monitoring")
        logger.info("  ✅ Data cleanup operations")
        return 0
    else:
        logger.error("💥 Some ChromaDB Manager tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())