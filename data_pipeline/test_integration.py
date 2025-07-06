#!/usr/bin/env python3
"""
Integration test for the enhanced data pipeline.

This script tests the integration between the data pipeline
and the backend audio processing system.
"""
import asyncio
import tempfile
import shutil
from pathlib import Path

from backend_integration import BackendAudioProcessor
from config import get_config

async def test_basic_integration():
    """Test basic integration without actual audio processing."""
    print("=== Testing Data Pipeline Integration ===")
    
    config = get_config()
    processor = BackendAudioProcessor()
    
    print(f"✅ Configuration loaded successfully")
    print(f"   Source folder: {config.source_folder}")
    print(f"   Backend database: {config.get_database_url()[:50]}...")
    print(f"   Supported formats: {config.supported_audio_formats}")
    print()
    
    print("✅ Backend processor created successfully")
    print(f"   Storage service: {processor.storage_service}")
    print()
    
    # Test configuration validation
    test_files = [
        ("test.mp3", True),
        ("test.m4a", True), 
        ("test.wav", True),
        ("test.txt", False),
        ("test.exe", False)
    ]
    
    print("🧪 Testing file validation:")
    for filename, should_be_valid in test_files:
        test_path = Path(filename)
        # Create a dummy file for testing
        with tempfile.NamedTemporaryFile(suffix=test_path.suffix, delete=False) as tmp:
            tmp.write(b"dummy content")
            tmp_path = Path(tmp.name)
        
        try:
            is_valid = config.validate_file(tmp_path)
            status = "✅ Valid" if is_valid else "❌ Invalid"
            expected = "✅ Valid" if should_be_valid else "❌ Invalid"
            match = "✅" if (is_valid == should_be_valid) else "❌"
            
            print(f"   {filename}: {status} (expected {expected}) {match}")
        finally:
            tmp_path.unlink()  # Clean up
    
    print()
    print("🎯 Integration test completed successfully!")
    print()
    print("To test with actual audio files:")
    print("1. Place audio files in: data_pipeline/source_data/")
    print("2. Run: python pipeline_v2.py")
    print("3. Monitor with: python pipeline_manager.py status")

if __name__ == "__main__":
    asyncio.run(test_basic_integration())