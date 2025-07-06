#!/usr/bin/env python3
"""Test script to verify configuration loading from .env files."""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set debug flag
os.environ["DEBUG_CONFIG"] = "1"

def test_config():
    """Test configuration loading."""
    print("Testing Pegasus Backend Configuration")
    print("=" * 50)
    
    try:
        from core.config import settings
        
        print("✅ Settings imported successfully")
        print()
        
        # Test core settings
        print("📋 Core Settings:")
        print(f"  API Title: {settings.api_title}")
        print(f"  Database URL: {settings.database_url}")
        print()
        
        # Test LLM settings
        print("🤖 LLM Settings:")
        print(f"  Provider: {settings.llm_provider}")
        print(f"  Timeout: {settings.llm_timeout}")
        print()
        
        # Test Ollama settings
        print("🦙 Ollama Settings:")
        print(f"  Model: {settings.ollama_model}")
        print(f"  Base URL: {settings.ollama_base_url}")
        print(f"  Timeout: {settings.ollama_timeout}")
        print()
        
        # Test Google AI settings
        print("🔍 Google Generative AI Settings:")
        print(f"  API Key: {'***' + (settings.google_generative_ai_api_key[-4:] if settings.google_generative_ai_api_key else 'Not set')}")
        print(f"  Model: {settings.google_generative_ai_model}")
        print()
        
        # Test database settings
        print("🗄️  Database Settings:")
        print(f"  Neo4j URI: {settings.neo4j_uri}")
        print(f"  ChromaDB Host: {settings.chromadb_host}:{settings.chromadb_port}")
        print()
        
        # Test transcription settings
        print("🎙️  Transcription Settings:")
        print(f"  Engine: {settings.transcription_engine}")
        print(f"  Whisper Model: {settings.whisper_model}")
        print(f"  Whisper Device: {settings.whisper_device}")
        print()
        
        print("✅ All settings loaded successfully!")
        
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)