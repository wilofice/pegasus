"""Ollama LLM client with session management support."""

from typing import Dict, List, Optional
from .base import BaseLLMClient
from services.ollama_service import OllamaService
from services.redis_session_manager import RedisSessionManager


class OllamaClient(BaseLLMClient):
    """Ollama LLM client with session management support."""
    
    def __init__(self):
        self.service = OllamaService()
        self.session_manager = RedisSessionManager()
        self._supports_sessions = True
    
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
    
    def create_session(self, user_id: str = None) -> str:
        """Create a new conversation session."""
        return self.session_manager.create_session(user_id=user_id)
    
    async def chat_with_session(self, session_id: str, message: str, user_id: str = None, **kwargs) -> str:
        """
        Chat with session management for conversation history.
        
        Args:
            session_id: Session ID for conversation continuity
            message: User message
            user_id: Optional user ID
            **kwargs: Additional parameters
            
        Returns:
            Assistant response
        """
        # Get conversation history
        history = self.session_manager.get_conversation_history(session_id, limit=10)
        
        # Add current user message to session
        self.session_manager.add_message(session_id, "user", message)
        
        # Build messages for chat
        messages = []
        
        # Add system prompt if provided
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Generate response
        response = await self.chat(messages, **kwargs)
        
        # Add assistant response to session
        self.session_manager.add_message(session_id, "assistant", response)
        
        return response
    
    def get_session_history(self, session_id: str, limit: int = None) -> List[Dict[str, any]]:
        """Get conversation history for a session."""
        return self.session_manager.get_conversation_history(session_id, limit=limit)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        return self.session_manager.delete_session(session_id)
    
    def set_session_context(self, session_id: str, context: Dict[str, any]) -> bool:
        """Set context data for a session."""
        return self.session_manager.set_context(session_id, context)
    
    def get_session_context(self, session_id: str) -> Dict[str, any]:
        """Get context data for a session."""
        return self.session_manager.get_context(session_id)
    
    async def health_check(self) -> Dict[str, any]:
        """Check Ollama service and session manager health."""
        ollama_health = await self.service.health_check()
        session_health = self.session_manager.health_check()
        
        return {
            "ollama": ollama_health,
            "sessions": session_health,
            "supports_sessions": self._supports_sessions
        }