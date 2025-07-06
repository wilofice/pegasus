"""Client for external LLM providers - supports Ollama and Google Generative AI."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, List
from enum import Enum
from abc import ABC, abstractmethod

import httpx
from services.ollama_service import OllamaService
from core.config import settings
LOGGER = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    GOOGLE_GENERATIVE_AI = "google_generative_ai"
    OPENAI = "openai"  # Legacy support


class BaseLLMClient(ABC):
    """Base class for LLM clients."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response from the LLM."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if the LLM service is healthy."""
        pass


class OllamaClient(BaseLLMClient):
    """Ollama LLM client using the existing OllamaService."""
    
    def __init__(self):
        self.service = OllamaService()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response using Ollama."""
        system_prompt = kwargs.get("system_prompt")
        result = await self.service.generate_completion(prompt, system_prompt)
        
        if result["success"]:
            return result["response"]
        else:
            raise RuntimeError(f"Ollama generation failed: {result.get('error', 'Unknown error')}")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response using Ollama."""
        # Convert chat messages to a single prompt for Ollama
        system_prompt = None
        prompt_parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_prompt = content
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        if prompt_parts:
            prompt += "\n\nAssistant:"
        
        return await self.generate(prompt, system_prompt=system_prompt, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health."""
        return await self.service.health_check()


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
    
    async def health_check(self) -> Dict[str, Any]:
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
    
    async def health_check(self) -> Dict[str, Any]:
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


class LLMClientFactory:
    """Factory for creating LLM clients based on configuration."""
    
    @staticmethod
    def create_client(provider: Optional[str] = None) -> BaseLLMClient:
        """Create an LLM client based on the provider configuration.
        
        Args:
            provider: Optional provider override. If not provided, uses LLM_PROVIDER env var.
            
        Returns:
            An instance of the appropriate LLM client.
            
        Raises:
            RuntimeError: If the provider is not supported or required configuration is missing.
        """
        # Determine provider from settings or parameter
        if provider is None:
            provider = settings.llm_provider.lower()
        else:
            provider = provider.lower()
        
        # Create appropriate client
        if provider == LLMProvider.OLLAMA:
            return OllamaClient()
        elif provider == LLMProvider.GOOGLE_GENERATIVE_AI or provider == "gemini":
            return GoogleGenerativeAIClient()
        elif provider == LLMProvider.OPENAI:
            return OpenAIClient()
        else:
            raise RuntimeError(f"Unsupported LLM provider: {provider}. Supported: {[p.value for p in LLMProvider]}")


# Global client instance (lazy initialization)
_llm_client: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClientFactory.create_client(settings.llm_provider)
    return _llm_client


# Legacy function for backward compatibility
async def generate(prompt: str) -> str:
    """Send the prompt to the LLM provider and return the answer.
    
    This is a legacy function maintained for backward compatibility.
    New code should use get_llm_client() or LLMClientFactory.
    """
    client = get_llm_client()
    return await client.generate(prompt)