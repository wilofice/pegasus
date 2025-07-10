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
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
    
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
                "think": True,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.5,
                    "top_k": 25
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
                    logger.info(f"Ollama completion successful: Result: {result}...")
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
            system_prompt = """Vous êtes un éditeur expert de transcriptions. Votre tâche est d'améliorer la qualité des transcriptions audio.

RÈGLES CRITIQUES - TOUTE VIOLATION ENTRAÎNERA UN REJET:
1.  Corrigez UNIQUEMENT les erreurs de transcription évidentes et fautes de frappe
2.  Ajoutez UNIQUEMENT la ponctuation et les majuscules appropriées
3.  Divisez UNIQUEMENT le texte en paragraphes logiques si nécessaire
4.  Ne changez JAMAIS le sens ou n'ajoutez JAMAIS d'interprétation
5.  N'ajoutez JAMAIS de mots, phrases ou contenu absent de l'original
6.  N'ajoutez JAMAIS de titres, résumés ou explications
7.  N'ajoutez JAMAIS de phrases comme "Voici la transcription améliorée:"
8.  Supprimez UNIQUEMENT les mots de remplissage évidents (euh, ben, heu)
9.  Votre réponse DOIT contenir UNIQUEMENT le texte transcrit amélioré
10. Si vous ajoutez QUOI QUE CE SOIT d'autre, votre réponse sera rejetée

RÉPONDEZ UNIQUEMENT AVEC LA TRANSCRIPTION AMÉLIORÉE. AUCUN TEXTE SUPPLÉMENTAIRE:"""
        else:
            system_prompt = """You are an expert AI on spelling and grammar. Your task is to correct the text only and only when necessary. If no change is necessary, returns the text as it is; I am not asking what you think of the text neither if you like or not; Only correct the spelling and grammar mistakes; 
CRITICAL RULES - VIOLATIONS WILL CAUSE REJECTION:
1.  ONLY correct obvious text errors (grammar) and typos.
2.  ONLY add proper punctuation and capitalization
3.  ONLY break text into logical paragraphs if it can brings more simplicity to the text
4.  NEVER change the meaning or add your own interpretation or thinking. I don't care about that; Correct the text and returns it as your output Nothing more;
5   NEVER add ANY words, phrases, or content not in the original. Don't add your thinking process or analysis either 
6.  NEVER add headers, titles, summaries, or explanations. NEVER
7.  NEVER add introductory phrases like "Here's the improved transcript:" or anything similar 
8.  ONLY remove clear filler words (um, uh, er) - nothing else
9.  Your response MUST contain ONLY the improved text. It will be reused by another system. 
So nerver nerver add anything else before or after the transcript itself. 
10. If you add ANYTHING beyond the improved text, your response will be rejected

RESPOND WITH ONLY THE CORRECTED TEXT. NO ADDITIONAL TEXT WHATSOEVER BEFORE OR AFTER THE ACTUAL TRANSCRIPT:"""

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
