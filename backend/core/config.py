"""Configuration settings for the Pegasus backend."""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    api_title: str = "Pegasus Backend"
    api_version: str = "0.1.0"
    
    # Database
    database_url: str = "postgresql://pegasus_user:pegasus_password@localhost:5432/pegasus_db"
    
    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "pegasus_neo4j_password"
    
    # ChromaDB Configuration
    chromadb_host: str = "localhost"
    chromadb_port: int = 8001
    chromadb_collection_name: str = "pegasus_transcripts"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "db+postgresql://pegasus_user:pegasus_password@localhost:5432/pegasus_db"
    max_workers: int = 4
    task_timeout: int = 300
    
    # Embeddings Configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # NLP Configuration
    spacy_model_en: str = "en_core_web_sm"
    spacy_model_fr: str = "fr_core_news_sm"
    
    # Plugin Configuration
    plugin_directory: str = "./plugins"
    plugin_enabled: bool = True
    
    # Audio Storage
    audio_storage_path: str = "./audio_files"
    max_file_size_mb: int = 100
    allowed_audio_formats: List[str] = ["m4a", "mp3", "wav", "ogg", "flac", "aac"]
    
    # Transcription
    transcription_engine: str = "whisper"  # "whisper" or "deepgram"
    whisper_model: str = "medium"
    whisper_device: str = "cuda"  # "cpu" or "cuda"
    deepgram_api_key: Optional[str] = None
    deepgram_api_url: str = "https://api.deepgram.com/v1/listen"
    
    # LLM Enhancement
    ollama_model: str = "gemma3:12b "
    ollama_timeout: int = 60
    ollama_base_url: str = "http://localhost:11434"
    enhancement_prompt_template: str = """You are a transcript editor. Your task is to correct the following transcript by:
1. Adding proper punctuation where needed
2. Fixing obvious grammatical errors
3. Ensuring proper capitalization

IMPORTANT RULES:
- Do NOT change the meaning or content
- Do NOT add or remove any words (except for fixing obvious typos)
- Keep the original speaker's style and tone
- Only output the corrected transcript, nothing else

Original transcript: {transcript}

Corrected transcript:"""
    
    # Security
    max_upload_size_bytes: int = 104857600  # 100MB
    allowed_mime_types: List[str] = [
        "audio/mp4",
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
        "audio/flac",
        "audio/aac",
        "audio/x-m4a"
    ]
    
    # Request/Response Logging
    enable_request_logging: bool = True
    log_directory: str = "./logs"
    log_max_body_size: int = 10000  # Max body size to log in bytes
    log_binary_content: bool = False
    log_excluded_paths: List[str] = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    log_excluded_methods: List[str] = []
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.audio_storage_path, exist_ok=True)