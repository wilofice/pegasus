"""Ollama service for transcript improvement using local LLM."""
import logging
from typing import Optional, Dict, Any
import httpx
import json

from core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for improving transcripts using Ollama local LLM."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'ollama_base_url', 'http://localhost:11434')
        self.model = getattr(settings, 'ollama_model', 'llama2')
        self.timeout = getattr(settings, 'ollama_timeout', 60.0)
    
    async def check_model_availability(self) -> bool:
        """Check if the Ollama model is available.
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models = response.json()
                    model_names = [model['name'] for model in models.get('models', [])]
                    return self.model in model_names
                
        except Exception as e:
            logger.error(f"Failed to check Ollama model availability: {e}")
        
        return False
    
    async def pull_model(self) -> bool:
        """Pull the model if it's not available.
        
        Returns:
            True if model was pulled successfully, False otherwise
        """
        try:
            logger.info(f"Pulling Ollama model: {self.model}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model},
                    timeout=300.0  # 5 minute timeout for model pull
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully pulled model: {self.model}")
                    return True
                else:
                    logger.error(f"Failed to pull model: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error pulling Ollama model: {e}")
        
        return False
    
    async def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate completion using Ollama.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            
        Returns:
            Dictionary with completion results
        """
        try:
            # Check if model is available
            if not await self.check_model_availability():
                logger.warning(f"Model {self.model} not available, attempting to pull...")
                if not await self.pull_model():
                    return {
                        "success": False,
                        "error": f"Model {self.model} is not available and could not be pulled"
                    }
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make request to Ollama
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "response": result.get("response", ""),
                        "model": result.get("model"),
                        "created_at": result.get("created_at"),
                        "done": result.get("done", True)
                    }
                else:
                    logger.error(f"Ollama API error {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}"
                    }
        
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def improve_transcript(self, transcript: str, context: Optional[str] = None, language: str = 'en') -> Dict[str, Any]:
        """Improve a transcript using Ollama LLM.
        
        Args:
            transcript: The original transcript to improve
            context: Optional context about the audio content
            language: Language code for the transcript (e.g., 'en', 'fr')
            
        Returns:
            Dictionary with improvement results
        """
        # Create language-specific system prompt
        if language == 'fr':
            system_prompt = """Vous êtes un éditeur expert de transcriptions. Votre tâche est d'améliorer la qualité des transcriptions audio en:

1. Corrigeant les erreurs évidentes de transcription et les fautes de frappe
2. Ajoutant la ponctuation et les majuscules appropriées
3. Divisant le texte en paragraphes logiques
4. Corrigeant la grammaire tout en préservant la voix naturelle du locuteur
5. Supprimant les mots de remplissage (euh, ben, genre) sauf s'ils ajoutent du sens
6. Maintenant le sens et le contenu originaux

Veuillez améliorer la transcription suivante en la gardant naturelle et lisible. IMPORTANT: Répondez UNIQUEMENT avec le texte amélioré, sans explications ni commentaires:"""
        else:
            system_prompt = """You are an expert transcript editor. Your task is to improve the quality of audio transcripts by:

1. Correcting obvious transcription errors and typos
2. Adding proper punctuation and capitalization
3. Breaking text into logical paragraphs
4. Correcting grammar while preserving the speaker's natural voice
5. Removing filler words (um, uh, like) unless they add meaning
6. Maintaining the original meaning and content

Please improve the following transcript while keeping it natural and readable. IMPORTANT: Respond ONLY with the improved text, no explanations or comments:"""

        user_prompt = f"Original transcript:\n\n{transcript}"
        
        if context:
            user_prompt = f"Context: {context}\n\n{user_prompt}"
        
        logger.info("Improving transcript with Ollama")
        result = await self.generate_completion(user_prompt, system_prompt)
        
        if result["success"]:
            improved_text = result["response"].strip()
            
            # Basic validation - improved text should not be empty or too short
            if len(improved_text) < len(transcript) * 0.3:
                logger.warning("Improved transcript seems too short, using original")
                return {
                    "success": False,
                    "error": "Improved transcript too short",
                    "original_transcript": transcript,
                    "improved_transcript": transcript
                }
            
            return {
                "success": True,
                "original_transcript": transcript,
                "improved_transcript": improved_text,
                "model": result.get("model"),
                "improvement_ratio": len(improved_text) / len(transcript) if transcript else 0
            }
        
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "original_transcript": transcript,
            "improved_transcript": transcript  # Fallback to original
        }
    
    async def generate_summary(self, transcript: str, max_length: int = 200) -> Dict[str, Any]:
        """Generate a summary of the transcript.
        
        Args:
            transcript: The transcript to summarize
            max_length: Maximum length of the summary in words
            
        Returns:
            Dictionary with summary results
        """
        system_prompt = f"""You are an expert at creating concise summaries. Create a {max_length}-word summary of the following transcript that captures the key points and main ideas. Focus on:

1. Main topics discussed
2. Key decisions or conclusions
3. Important details or numbers
4. Action items if any

Keep the summary clear, concise, and informative."""

        user_prompt = f"Transcript to summarize:\n\n{transcript}"
        
        logger.info("Generating transcript summary with Ollama")
        result = await self.generate_completion(user_prompt, system_prompt)
        
        if result["success"]:
            return {
                "success": True,
                "summary": result["response"].strip(),
                "original_length": len(transcript.split()),
                "summary_length": len(result["response"].strip().split()),
                "model": result.get("model")
            }
        
        return {
            "success": False,
            "error": result.get("error", "Unknown error")
        }
    
    async def extract_keywords(self, transcript: str, max_keywords: int = 10) -> Dict[str, Any]:
        """Extract keywords from the transcript.
        
        Args:
            transcript: The transcript to analyze
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            Dictionary with keyword extraction results
        """
        system_prompt = f"""Extract up to {max_keywords} important keywords or key phrases from the following transcript. Focus on:

1. Main topics and subjects
2. Important names, places, or organizations
3. Technical terms or concepts
4. Key actions or events

Return only the keywords, separated by commas, without explanations."""

        user_prompt = f"Extract keywords from this transcript:\n\n{transcript}"
        
        logger.info("Extracting keywords with Ollama")
        result = await self.generate_completion(user_prompt, system_prompt)
        
        if result["success"]:
            keywords_text = result["response"].strip()
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            
            return {
                "success": True,
                "keywords": keywords[:max_keywords],
                "model": result.get("model")
            }
        
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "keywords": []
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health.
        
        Returns:
            Dictionary with health status
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    models = response.json()
                    return {
                        "healthy": True,
                        "available_models": [model['name'] for model in models.get('models', [])],
                        "configured_model": self.model,
                        "model_available": self.model in [model['name'] for model in models.get('models', [])]
                    }
        
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
        
        return {
            "healthy": False,
            "error": "Service unavailable"
        }