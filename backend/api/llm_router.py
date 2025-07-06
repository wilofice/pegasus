"""LLM service management API routes."""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from services.llm_client import get_llm_client, LLMClientFactory, LLMProvider
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/health")
async def check_llm_health():
    """Check the health status of the configured LLM service.
    
    Returns:
        Health status including provider info and availability
    """
    try:
        client = get_llm_client()
        health = await client.health_check()
        
        return {
            "status": "healthy" if health.get("healthy") else "unhealthy",
            "details": health
        }
        
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {
            "status": "error",
            "details": {
                "healthy": False,
                "error": str(e)
            }
        }


@router.get("/providers")
async def list_providers():
    """List available LLM providers and current configuration.
    
    Returns:
        Available providers and current selection
    """
    current_provider = settings.llm_provider.lower()
    
    return {
        "available_providers": [p.value for p in LLMProvider],
        "current_provider": current_provider,
        "provider_descriptions": {
            "ollama": "Local LLM using Ollama (privacy-focused, offline-capable)",
            "google_generative_ai": "Google's Gemini models (state-of-the-art, cloud-based)",
            "openai": "OpenAI GPT models (legacy support)"
        }
    }


@router.post("/test")
async def test_llm_generation(
    prompt: str = Query(..., description="Test prompt for LLM"),
    provider: Optional[str] = Query(None, description="Optional provider override")
):
    """Test LLM generation with a custom prompt.
    
    Args:
        prompt: The test prompt to send to the LLM
        provider: Optional provider to use (overrides default)
        
    Returns:
        Generated response and metadata
    """
    try:
        # Use specified provider or default
        if provider:
            client = LLMClientFactory.create_client(provider)
        else:
            client = get_llm_client()
        
        # Generate response
        response = await client.generate(prompt)
        
        # Get provider info
        health = await client.health_check()
        
        return {
            "success": True,
            "prompt": prompt,
            "response": response,
            "provider": health.get("provider", "unknown"),
            "model": health.get("configured_model", "unknown")
        }
        
    except Exception as e:
        logger.error(f"LLM test generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {str(e)}"
        )


@router.post("/chat/test")
async def test_llm_chat(
    messages: list[Dict[str, str]],
    provider: Optional[str] = Query(None, description="Optional provider override")
):
    """Test LLM chat completion with messages.
    
    Args:
        messages: List of chat messages with role and content
        provider: Optional provider to use (overrides default)
        
    Returns:
        Generated chat response and metadata
    """
    try:
        # Validate messages
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content' fields")
        
        # Use specified provider or default
        if provider:
            client = LLMClientFactory.create_client(provider)
        else:
            client = get_llm_client()
        
        # Generate response
        response = await client.chat(messages)
        
        # Get provider info
        health = await client.health_check()
        
        return {
            "success": True,
            "messages": messages,
            "response": response,
            "provider": health.get("provider", "unknown"),
            "model": health.get("configured_model", "unknown")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LLM chat test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"LLM chat failed: {str(e)}"
        )