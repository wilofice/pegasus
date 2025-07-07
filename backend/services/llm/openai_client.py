"""Legacy OpenAI client."""

import logging
import httpx
from typing import Dict, List
from .base import BaseLLMClient
from core.config import settings

LOGGER = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """Legacy OpenAI client for backward compatibility."""
    
    def __init__(self):
        self.api_key = settings.openai_api_key or settings.llm_api_key
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY or LLM_API_KEY not configured in settings")
        
        self.base_url = settings.openai_api_url
        self.model = settings.openai_model
        self.timeout = settings.llm_timeout
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate using OpenAI completion API (legacy)."""
        # Convert to chat format for newer models
        messages = [{"role": "user", "content": prompt}]
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        return await self.chat(messages, **kwargs)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate using OpenAI chat API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 256),
            "top_p": kwargs.get("top_p", 1.0),
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    choices = result.get("choices", [])
                    if choices:
                        return choices[0]["message"]["content"]
                    raise RuntimeError("No choices in response")
                else:
                    error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                    LOGGER.error(error_msg)
                    raise RuntimeError(error_msg)
                    
        except httpx.TimeoutException:
            raise RuntimeError("OpenAI request timed out")
        except Exception as e:
            if not isinstance(e, RuntimeError):
                LOGGER.error(f"OpenAI error: {e}")
                raise RuntimeError(f"OpenAI error: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, any]:
        """Check OpenAI service health."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [model["id"] for model in models_data.get("data", [])]
                    
                    return {
                        "healthy": True,
                        "provider": "openai",
                        "configured_model": self.model,
                        "available_models": available_models,
                        "model_available": self.model in available_models
                    }
                else:
                    return {
                        "healthy": False,
                        "provider": "openai",
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            LOGGER.error(f"OpenAI health check failed: {e}")
            return {
                "healthy": False,
                "provider": "openai",
                "error": str(e)
            }