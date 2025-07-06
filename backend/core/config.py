"""Configuration settings for the Pegasus backend."""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


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
    
    # LLM Configuration
    llm_provider: str = "ollama"  # "ollama", "google_generative_ai", or "openai"
    llm_timeout: float = 30.0  # General LLM timeout in seconds
    
    # Ollama Configuration
    ollama_model: str = "llama2"
    ollama_timeout: float = 60.0
    ollama_base_url: str = "http://localhost:11434"
    
    # Google Generative AI Configuration
    google_generative_ai_api_key: Optional[str] = None
    google_generative_ai_model: str = "gemini-pro"
    gemini_api_key: Optional[str] = None  # Alternative env var name
    
    # OpenAI Configuration (Legacy)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_api_url: str = "https://api.openai.com/v1"
    llm_api_key: Optional[str] = None  # Legacy env var name
    
    # LLM Enhancement Settings
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

    # New settings for conversation history and prompt enhancement
    conversation_history_lookback_days: int = 1
    conversation_processing_delay_minutes: int = 5
    recent_transcript_window_hours: int = 12
    
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
    
    model_config = SettingsConfigDict(
        env_file=[
            Path(__file__).parent / ".env",  # backend/core/.env
            Path(__file__).parent.parent / ".env",  # backend/.env
            ".env"  # Current working directory
        ],
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider is supported."""
        valid_providers = ['ollama', 'google_generative_ai', 'openai']
        if v not in valid_providers:
            raise ValueError(f'LLM provider must be one of: {valid_providers}')
        return v
    
    @field_validator('transcription_engine')
    @classmethod
    def validate_transcription_engine(cls, v):
        """Validate transcription engine is supported."""
        valid_engines = ['whisper', 'deepgram']
        if v not in valid_engines:
            raise ValueError(f'Transcription engine must be one of: {valid_engines}')
        return v


# Create settings instance
settings = Settings()

# Debug: Print which .env files were found and loaded
def _debug_env_files():
    """Debug function to show which .env files are being loaded."""
    env_files = [
        Path(__file__).parent / ".env",  # backend/core/.env
        Path(__file__).parent.parent / ".env",  # backend/.env
        Path(".env")  # Current working directory
    ]
    
    print("🔧 Environment Configuration Debug:")
    print(f"Current working directory: {os.getcwd()}")
    
    for env_file in env_files:
        if env_file.exists():
            print(f"✅ Found .env file: {env_file.absolute()}")
        else:
            print(f"❌ Missing .env file: {env_file.absolute()}")
    
    print(f"🎯 LLM Provider: {settings.llm_provider}")
    print(f"🎯 Ollama Model: {settings.ollama_model}")
    print(f"🎯 Database URL: {settings.database_url[:50]}...")
    print("=" * 50)

# Run debug if DEBUG env var is set
if os.getenv("DEBUG_CONFIG"):
    _debug_env_files()

# Create directories if they don't exist
os.makedirs(settings.audio_storage_path, exist_ok=True)
os.makedirs(settings.log_directory, exist_ok=True)