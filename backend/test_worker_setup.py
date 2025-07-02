#!/usr/bin/env python3
"""Test script for validating worker setup without requiring external services."""
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_chunking_service():
    """Test chunking service."""
    try:
        from services.chunking_service import ChunkingService
        
        chunker = ChunkingService(chunk_size=100, overlap_size=20)
        
        test_text = """
        This is a test document for chunking. It contains multiple sentences that should be split into chunks.
        The chunking service should handle overlapping properly. Each chunk should maintain readability.
        We want to test that the service can handle various text lengths and punctuation marks correctly.
        This text is long enough to be split into multiple chunks for testing purposes.
        """
        
        chunks = chunker.chunk_text(test_text.strip())
        
        logger.info(f"✅ ChunkingService: Created {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i}: {len(chunk.text)} chars, positions {chunk.start}-{chunk.end}")
        
        # Test statistics
        stats = chunker.get_chunk_stats(chunks)
        logger.info(f"  Stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ChunkingService test failed: {e}")
        return False


def test_ner_service():
    """Test NER service."""
    try:
        from services.ner_service import NERService
        
        ner_service = NERService()
        
        test_texts = [
            "John Doe works at OpenAI in San Francisco.",
            "Apple Inc. was founded by Steve Jobs in Cupertino, California.",
            "The meeting is scheduled for January 15th, 2024 at Microsoft."
        ]
        
        for text in test_texts:
            entities = ner_service.extract_entities(text)
            logger.info(f"  Text: '{text}'")
            for entity in entities:
                logger.info(f"    Entity: {entity['text']} ({entity['label']}) - {entity['label_description']}")
        
        # Test supported languages
        languages = ner_service.get_supported_languages()
        logger.info(f"✅ NERService: Supports languages: {languages}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ NERService test failed: {e}")
        return False


def test_graph_builder():
    """Test graph builder (import only, no Neo4j connection)."""
    try:
        from services.graph_builder import GraphBuilder
        
        # Just test import - no actual connection needed
        logger.info("✅ GraphBuilder: Import successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ GraphBuilder test failed: {e}")
        return False


def test_celery_setup():
    """Test Celery app configuration."""
    try:
        from workers.celery_app import app
        
        # Test basic Celery app configuration
        logger.info(f"✅ Celery app configured: {app.main}")
        logger.info(f"  Broker URL: {app.conf.broker_url}")
        logger.info(f"  Result backend: {app.conf.result_backend}")
        
        # Test task discovery
        tasks = list(app.tasks.keys())
        logger.info(f"  Discovered tasks: {len(tasks)}")
        
        for task in tasks:
            if 'transcript' in task or 'health' in task:
                logger.info(f"    - {task}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Celery setup test failed: {e}")
        return False


def test_task_imports():
    """Test task imports."""
    try:
        from workers.tasks.transcript_processor import process_transcript, reprocess_transcript
        
        logger.info("✅ Task imports successful:")
        logger.info(f"  - process_transcript: {process_transcript.name}")
        logger.info(f"  - reprocess_transcript: {reprocess_transcript.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Task imports failed: {e}")
        return False


def test_config_validation():
    """Test configuration validation."""
    try:
        from workers.config import task_routes, task_queues
        
        logger.info("✅ Worker configuration:")
        logger.info(f"  Task routes: {len(task_routes)} configured")
        logger.info(f"  Task queues: {len(task_queues)} configured")
        
        for route, queue_info in task_routes.items():
            logger.info(f"    {route} -> {queue_info}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Config validation failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("🧪 Running Celery Worker Setup Tests (without external services)")
    
    tests = [
        ("Chunking Service", test_chunking_service),
        ("NER Service", test_ner_service),
        ("Graph Builder Import", test_graph_builder),
        ("Celery Configuration", test_celery_setup),
        ("Task Imports", test_task_imports),
        ("Configuration Validation", test_config_validation),
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
        logger.info("🎉 All tests passed! Celery worker setup is ready.")
        logger.info("\n📋 Next steps:")
        logger.info("  1. Start Redis: docker compose up redis -d")
        logger.info("  2. Start Neo4j: docker compose up neo4j -d")  
        logger.info("  3. Start ChromaDB: docker compose up chromadb -d")
        logger.info("  4. Start PostgreSQL: docker compose up postgres -d")
        logger.info("  5. Run migrations: cd backend && alembic upgrade head")
        logger.info("  6. Start worker: cd backend && python start_worker.py")
        return 0
    else:
        logger.error("💥 Some tests failed. Check the logs above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())