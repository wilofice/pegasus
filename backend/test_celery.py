#!/usr/bin/env python3
"""Test script for Celery worker functionality."""
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_worker_health():
    """Test basic worker health check."""
    try:
        from workers.celery_app import health_check
        
        logger.info("Testing worker health check...")
        result = health_check.delay()
        
        # Wait for result with timeout
        health_result = result.get(timeout=30)
        
        if health_result.get('status') == 'healthy':
            logger.info("✅ Worker health check passed")
            logger.info(f"Worker ID: {health_result.get('worker_id')}")
            logger.info(f"Neo4j: {health_result.get('neo4j')}")
            logger.info(f"ChromaDB: {health_result.get('chromadb')}")
            return True
        else:
            logger.error("❌ Worker health check failed")
            logger.error(f"Result: {health_result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health check test failed: {e}")
        return False


def test_transcript_processing():
    """Test transcript processing task."""
    try:
        from workers.tasks.transcript_processor import process_transcript
        
        # This would require an actual audio file in the database
        # For now, just test that the task can be imported and called
        logger.info("Testing transcript processing task import...")
        
        # Test with invalid input to see if validation works
        try:
            result = process_transcript.delay("")
            result.get(timeout=5)
            logger.error("❌ Expected validation error for empty audio_id")
            return False
        except Exception as e:
            if "audio_id is required" in str(e):
                logger.info("✅ Transcript processor validation working")
                return True
            else:
                logger.error(f"❌ Unexpected error: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Transcript processing test failed: {e}")
        return False


def test_services():
    """Test that all required services can be imported and initialized."""
    try:
        logger.info("Testing service imports...")
        
        # Test chunking service
        from services.chunking_service import ChunkingService
        chunker = ChunkingService()
        chunks = chunker.chunk_text("This is a test text for chunking.")
        logger.info(f"✅ ChunkingService: Created {len(chunks)} chunks")
        
        # Test NER service
        from services.ner_service import NERService
        ner_service = NERService()
        entities = ner_service.extract_entities("John Doe works at OpenAI in San Francisco.")
        logger.info(f"✅ NERService: Extracted {len(entities)} entities")
        
        # Test graph builder (without Neo4j connection)
        from services.graph_builder import GraphBuilder
        logger.info("✅ GraphBuilder: Import successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("🧪 Running Celery worker tests...")
    
    tests = [
        ("Service Imports", test_services),
        ("Worker Health Check", test_worker_health),
        ("Transcript Processing", test_transcript_processing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Celery worker setup is working correctly.")
        return 0
    else:
        logger.error("💥 Some tests failed. Check the logs above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())