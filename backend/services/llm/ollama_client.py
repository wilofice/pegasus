"""Ollama LLM client."""

from typing import Dict, List
from .base import BaseLLMClient
from services.ollama_service import OllamaService


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
    
    async def health_check(self) -> Dict[str, any]:
        """Check Ollama service health."""
        return await self.service.health_check()