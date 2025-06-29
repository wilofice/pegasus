"""Audio transcription service using Whisper and Deepgram."""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
import whisper
import asyncio
from concurrent.futures import ThreadPoolExecutor

from core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files using multiple engines."""
    
    def __init__(self):
        self._whisper_model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def _load_whisper_model(self):
        """Load Whisper model (lazy loading)."""
        if self._whisper_model is None:
            model_size = getattr(settings, 'whisper_model_size', 'base')
            logger.info(f"Loading Whisper model: {model_size}")
            self._whisper_model = whisper.load_model(model_size)
        return self._whisper_model
    
    async def transcribe_with_whisper(self, file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Run Whisper in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._transcribe_whisper_sync,
                file_path
            )
            
            return {
                "success": True,
                "transcript": result["text"],
                "language": result.get("language"),
                "segments": result.get("segments", []),
                "engine": "whisper"
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription failed for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "engine": "whisper"
            }
    
    def _transcribe_whisper_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous Whisper transcription (runs in thread pool)."""
        model = self._load_whisper_model()
        
        # Transcribe the audio
        result = model.transcribe(
            file_path,
            language=None,  # Auto-detect language
            word_timestamps=True,
            verbose=False
        )
        
        return result
    
    async def transcribe_with_deepgram(self, file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Deepgram API.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary with transcription results
        """
        if not hasattr(settings, 'deepgram_api_key') or not settings.deepgram_api_key:
            return {
                "success": False,
                "error": "Deepgram API key not configured",
                "engine": "deepgram"
            }
        
        try:
            # Read audio file
            with open(file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Prepare Deepgram API request
            headers = {
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": "audio/mp4"  # Adjust based on file type
            }
            
            params = {
                "model": "nova-2",
                "language": "en",
                "smart_format": "true",
                "punctuate": "true",
                "diarize": "false",
                "timestamps": "true"
            }
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepgram.com/v1/listen",
                    headers=headers,
                    params=params,
                    content=audio_data,
                    timeout=120.0  # 2 minute timeout
                )
                
                if response.status_code != 200:
                    logger.error(f"Deepgram API error {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "engine": "deepgram"
                    }
                
                result = response.json()
                
                # Extract transcript from response
                transcript = ""
                if "results" in result and "channels" in result["results"]:
                    for channel in result["results"]["channels"]:
                        for alternative in channel.get("alternatives", []):
                            transcript += alternative.get("transcript", "")
                
                return {
                    "success": True,
                    "transcript": transcript,
                    "language": result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("language"),
                    "confidence": result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("confidence"),
                    "full_response": result,
                    "engine": "deepgram"
                }
                
        except Exception as e:
            logger.error(f"Deepgram transcription failed for {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "engine": "deepgram"
            }
    
    async def transcribe_audio(
        self,
        file_path: str,
        engine: str = "auto"
    ) -> Dict[str, Any]:
        """Transcribe audio file using the specified engine.
        
        Args:
            file_path: Path to the audio file
            engine: Transcription engine ("whisper", "deepgram", or "auto")
            
        Returns:
            Dictionary with transcription results
        """
        if not Path(file_path).exists():
            return {
                "success": False,
                "error": "Audio file not found",
                "engine": engine
            }
        
        # Auto-select engine based on configuration
        if engine == "auto":
            # Prefer Deepgram if API key is available, otherwise use Whisper
            if hasattr(settings, 'deepgram_api_key') and settings.deepgram_api_key:
                engine = "deepgram"
            else:
                engine = "whisper"
        
        logger.info(f"Transcribing {file_path} with {engine}")
        
        # Call appropriate transcription method
        if engine == "whisper":
            return await self.transcribe_with_whisper(file_path)
        elif engine == "deepgram":
            return await self.transcribe_with_deepgram(file_path)
        else:
            return {
                "success": False,
                "error": f"Unknown transcription engine: {engine}",
                "engine": engine
            }
    
    def get_supported_engines(self) -> list[str]:
        """Get list of supported transcription engines.
        
        Returns:
            List of engine names
        """
        engines = ["whisper"]
        
        if hasattr(settings, 'deepgram_api_key') and settings.deepgram_api_key:
            engines.append("deepgram")
        
        return engines
    
    async def get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get duration of audio file in seconds.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Duration in seconds or None if unable to determine
        """
        try:
            # Use ffprobe if available, otherwise estimate from file size
            import subprocess
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", file_path
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
                
        except Exception as e:
            logger.warning(f"Could not determine audio duration for {file_path}: {e}")
        
        return None