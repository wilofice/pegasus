"""LLM client module - legacy compatibility layer.

This module provides backward compatibility imports for the refactored LLM client structure.
New code should import directly from services.llm instead.
"""

# Import everything from the new LLM package for backward compatibility
from .llm import *

# Explicit imports for better IDE support
from .llm.base import BaseLLMClient, LLMProvider, VertexSession, VertexEvent
from .llm.factory import LLMClientFactory, get_llm_client, generate
from .llm.ollama_client import OllamaClient
from .llm.google_client import GoogleGenerativeAIClient
from .llm.vertex_client import VertexAIClient
from .llm.openai_client import OpenAIClient

__all__ = [
    'BaseLLMClient',
    'LLMProvider',
    'VertexSession', 
    'VertexEvent',
    'LLMClientFactory',
    'get_llm_client',
    'generate',
    'OllamaClient',
    'GoogleGenerativeAIClient',
    'VertexAIClient', 
    'OpenAIClient'
]