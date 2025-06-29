#!/usr/bin/env python3
"""Test script for the audio upload API."""
import asyncio
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from core.database import async_session
from models.audio_file import AudioFile, ProcessingStatus
from repositories.audio_repository import AudioRepository
from services.audio_storage import AudioStorageService
from services.transcription_service import TranscriptionService
from services.ollama_service import OllamaService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection and audio repository."""
    try:
        async with async_session() as db:
            audio_repo = AudioRepository(db)
            
            # Create a test record
            test_data = {
                "filename": "test_audio.m4a",
                "original_filename": "test.m4a",
                "file_path": "/tmp/test_audio.m4a",
                "file_size_bytes": 1024,
                "mime_type": "audio/mp4",
                "user_id": "test_user",
                "processing_status": ProcessingStatus.UPLOADED
            }
            
            audio_file = await audio_repo.create(test_data)
            logger.info(f"✅ Created test audio record: {audio_file.id}")
            
            # Test retrieval
            retrieved = await audio_repo.get_by_id(audio_file.id)
            assert retrieved is not None
            logger.info(f"✅ Retrieved audio record: {retrieved.filename}")
            
            # Test status update
            updated = await audio_repo.update_status(
                audio_file.id, 
                ProcessingStatus.COMPLETED
            )
            assert updated.processing_status == ProcessingStatus.COMPLETED
            logger.info(f"✅ Updated status to: {updated.processing_status}")
            
            # Cleanup
            await audio_repo.delete(audio_file.id)
            logger.info("✅ Cleaned up test record")
            
            logger.info("✅ Database tests passed!")
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        raise


async def test_transcription_service():
    """Test transcription service initialization."""
    try:
        service = TranscriptionService()
        engines = service.get_supported_engines()
        logger.info(f"✅ Transcription service initialized. Engines: {engines}")
        
        # Test invalid file path
        result = await service.transcribe_audio("/nonexistent/file.m4a")
        assert not result["success"]
        assert "not found" in result["error"]
        logger.info("✅ Transcription service handles missing files correctly")
        
    except Exception as e:
        logger.error(f"❌ Transcription service test failed: {e}")
        raise


async def test_ollama_service():
    """Test Ollama service initialization."""
    try:
        service = OllamaService()
        health = await service.health_check()
        
        if health["healthy"]:
            logger.info(f"✅ Ollama service is healthy. Models: {health.get('available_models', [])}")
            
            # Test transcript improvement with dummy data
            test_transcript = "um this is a test transcript with some uh filler words"
            result = await service.improve_transcript(test_transcript)
            
            if result["success"]:
                logger.info(f"✅ Transcript improvement test passed")
                logger.info(f"   Original: {result['original_transcript']}")
                logger.info(f"   Improved: {result['improved_transcript']}")
            else:
                logger.warning(f"⚠️ Transcript improvement failed (service may not be running): {result.get('error')}")
        else:
            logger.warning(f"⚠️ Ollama service not healthy (may not be running): {health.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Ollama service test failed: {e}")
        raise


async def test_audio_storage():
    """Test audio storage service."""
    try:
        service = AudioStorageService()
        logger.info("✅ Audio storage service initialized")
        
        # Test file path generation
        filename, file_path = service._generate_unique_filename("test.m4a")
        assert filename.endswith(".m4a")
        assert len(filename) > 10  # Should have timestamp and random ID
        logger.info(f"✅ Generated filename: {filename}")
        
        # Test directory structure
        from datetime import datetime
        expected_date_part = datetime.now().strftime("%Y/%m/%d")
        assert expected_date_part in file_path
        logger.info(f"✅ File path includes date structure: {expected_date_part}")
        
    except Exception as e:
        logger.error(f"❌ Audio storage test failed: {e}")
        raise


async def run_all_tests():
    """Run all tests."""
    logger.info("🧪 Starting audio API tests...")
    
    try:
        await test_database_connection()
        await test_transcription_service()
        await test_ollama_service()
        await test_audio_storage()
        
        logger.info("🎉 All tests passed!")
        
    except Exception as e:
        logger.error(f"💥 Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if database is initialized
    import os
    if not os.path.exists("alembic.ini"):
        logger.error("❌ Database not initialized. Run 'python scripts/init_db.py' first")
        sys.exit(1)
    
    asyncio.run(run_all_tests())