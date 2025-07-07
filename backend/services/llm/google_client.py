"""Google Generative AI (Gemini) client."""

import logging
import httpx
from typing import Dict, List
from .base import BaseLLMClient
from core.config import settings

LOGGER = logging.getLogger(__name__)


class GoogleGenerativeAIClient(BaseLLMClient):
    """Google Generative AI (Gemini) client."""
    
    def __init__(self):
        # Use primary API key or fallback to alternative env var name
        self.api_key = settings.google_generative_ai_api_key or settings.gemini_api_key
        if not self.api_key:
            raise RuntimeError("GOOGLE_GENERATIVE_AI_API_KEY or GEMINI_API_KEY not configured in settings")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = settings.google_generative_ai_model
        self.timeout = settings.llm_timeout
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response using Google Generative AI."""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Prepare the request payload
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topK": kwargs.get("top_k", 40),
                "topP": kwargs.get("top_p", 0.95),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            }
        }
        
        # Add system instruction if provided using dedicated parameter
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            data["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    if candidates and candidates[0].get("content"):
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0]["text"]
                    
                    raise RuntimeError("No text content in response")
                else:
                    error_msg = f"Google Generative AI API error: {response.status_code} - {response.text}"
                    LOGGER.error(error_msg)
                    raise RuntimeError(error_msg)
                    
        except httpx.TimeoutException:
            raise RuntimeError("Google Generative AI request timed out")
        except Exception as e:
            if not isinstance(e, RuntimeError):
                LOGGER.error(f"Google Generative AI error: {e}")
                raise RuntimeError(f"Google Generative AI error: {str(e)}")
            raise
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response using Google Generative AI."""
        headers = {
            "Content-Type": "application/json",
        }
        
        # Convert messages to Google format
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Google uses "user" and "model" roles
            if role == "system":
                # Use dedicated systemInstruction parameter
                system_instruction = {
                    "parts": [{"text": content}]
                }
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            else:  # user
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topK": kwargs.get("top_k", 40),
                "topP": kwargs.get("top_p", 0.95),
                "maxOutputTokens": kwargs.get("max_tokens", 2048),
            }
        }
        
        # Add system instruction if provided
        if system_instruction:
            data["systemInstruction"] = system_instruction
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    if candidates and candidates[0].get("content"):
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0]["text"]
                    
                    raise RuntimeError("No text content in response")
                else:
                    error_msg = f"Google Generative AI API error: {response.status_code} - {response.text}"
                    LOGGER.error(error_msg)
                    raise RuntimeError(error_msg)
                    
        except httpx.TimeoutException:
            raise RuntimeError("Google Generative AI request timed out")
        except Exception as e:
            if not isinstance(e, RuntimeError):
                LOGGER.error(f"Google Generative AI chat error: {e}")
                raise RuntimeError(f"Google Generative AI chat error: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, any]:
        """Check Google Generative AI service health."""
        try:
            # Try to list available models
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models?key={self.api_key}",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [
                        model["name"].split("/")[-1] 
                        for model in models_data.get("models", [])
                        if "generateContent" in model.get("supportedGenerationMethods", [])
                    ]
                    
                    return {
                        "healthy": True,
                        "provider": "google_generative_ai",
                        "configured_model": self.model,
                        "available_models": available_models,
                        "model_available": self.model in available_models
                    }
                else:
                    return {
                        "healthy": False,
                        "provider": "google_generative_ai",
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            LOGGER.error(f"Google Generative AI health check failed: {e}")
            return {
                "healthy": False,
                "provider": "google_generative_ai",
                "error": str(e)
            }