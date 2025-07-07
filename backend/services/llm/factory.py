"""LLM client factory and global client management."""

from typing import Optional
from .base import BaseLLMClient, LLMProvider
from core.config import settings


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
            from .ollama_client import OllamaClient
            return OllamaClient()
        elif provider == LLMProvider.GOOGLE_GENERATIVE_AI or provider == "gemini":
            from .google_client import GoogleGenerativeAIClient
            return GoogleGenerativeAIClient()
        elif provider == LLMProvider.VERTEX_AI:
            from .vertex_client import VertexAIClient
            return VertexAIClient()
        elif provider == LLMProvider.OPENAI:
            from .openai_client import OpenAIClient
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