"""
Configuration management for data pipeline.

This module ensures the data pipeline uses the same configuration
as the backend for consistency and shared settings.
"""
import os
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Import backend settings
from core.config import settings as backend_settings

# Data pipeline specific settings
class DataPipelineConfig:
    """
    Configuration class that extends backend settings with pipeline-specific options.
    """
    
    def __init__(self):
        # Use backend settings as base
        self.backend = backend_settings
        
        # Pipeline-specific settings
        self.source_folder = Path(__file__).parent / "source_data"
        self.processed_folder = Path(__file__).parent / "processed"
        self.log_folder = Path(__file__).parent / "logs"
        
        # Create folders if they don't exist
        for folder in [self.source_folder, self.processed_folder, self.log_folder]:
            folder.mkdir(exist_ok=True)
        
        # File watching settings
        self.watch_recursive = False
        self.processing_timeout = 300  # 5 minutes
        
        # Integration settings
        self.default_user_id = "data_pipeline"
        self.default_language = "en"
        
        # Webhook settings (reuse existing notifier logic)
        self.webhook_enabled = os.getenv("PIPELINE_WEBHOOK_ENABLED", "true").lower() == "true"
        self.webhook_url = os.getenv("PIPELINE_WEBHOOK_URL", "http://localhost:8000/api/webhook")
    
    @property
    def supported_audio_formats(self):
        """Get supported audio formats from backend settings."""
        return self.backend.allowed_audio_formats
    
    @property
    def max_file_size_bytes(self):
        """Get max file size from backend settings."""
        return self.backend.max_upload_size_bytes
    
    @property
    def transcription_engine(self):
        """Get transcription engine from backend settings."""
        return self.backend.transcription_engine
    
    @property
    def whisper_model(self):
        """Get Whisper model from backend settings."""
        return self.backend.whisper_model
    
    @property
    def ollama_enabled(self):
        """Check if Ollama is available for transcript improvement."""
        return hasattr(self.backend, 'ollama_base_url') and self.backend.ollama_base_url
    
    def get_database_url(self):
        """Get database URL from backend settings."""
        return self.backend.database_url
    
    def get_chromadb_config(self):
        """Get ChromaDB configuration from backend settings."""
        return {
            "host": self.backend.chromadb_host,
            "port": self.backend.chromadb_port,
            "collection_name": self.backend.chromadb_collection_name
        }
    
    def get_audio_storage_path(self):
        """Get audio storage path from backend settings."""
        return self.backend.audio_storage_path
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate if file can be processed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is valid for processing
        """
        # Check file extension
        if file_path.suffix.lower() not in [f".{fmt}" for fmt in self.supported_audio_formats]:
            return False
        
        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                return False
        except OSError:
            return False
        
        return True
    
    def __repr__(self):
        return f"DataPipelineConfig(source_folder={self.source_folder})"


# Global configuration instance
config = DataPipelineConfig()

# Convenience functions
def get_config():
    """Get the global configuration instance."""
    return config

def get_backend_settings():
    """Get the backend settings."""
    return backend_settings