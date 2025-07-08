"""Base classes and types for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    GOOGLE_GENERATIVE_AI = "google_generative_ai"
    VERTEX_AI = "vertex_ai"
    VERTEX_ADK = "vertex_adk"  # Vertex AI Agent Development Kit
    OPENAI = "openai"  # Legacy support


@dataclass
class VertexSession:
    """Represents a Vertex AI session."""
    id: str
    user_id: str
    created_at: datetime
    state: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VertexSession':
        """Create a VertexSession from API response."""
        return cls(
            id=data.get("name", "").split("/")[-1],
            user_id=data.get("userId", ""),
            created_at=datetime.fromisoformat(data.get("createTime", "").replace("Z", "+00:00")),
            state=data.get("state", {})
        )


@dataclass
class VertexEvent:
    """Represents a Vertex AI session event."""
    author: str
    invocation_id: str
    timestamp: float
    content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Vertex AI Agent Engine API format."""
        from datetime import datetime
        
        # Convert Unix timestamp to RFC3339 format for Protobuf Timestamp
        timestamp_rfc3339 = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        event_data = {
            "author": self.author,
            "invocationId": self.invocation_id,
            "timestamp": timestamp_rfc3339
        }
        
        # Format content as Content object if provided
        if self.content:
            event_data["content"] = {
                "parts": [
                    {
                        "text": self.content
                    }
                ]
            }
        
        return event_data


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
    
    # Session management methods (optional, only implemented by clients that support it)
    async def create_session(self, user_id: str = None, **kwargs) -> Optional[str]:
        """Create a new session for the user. Returns session ID if supported."""
        return None
    
    async def get_session(self, session_id: str, user_id: str = None) -> Optional[Any]:
        """Get session details if supported."""
        return None
    
    async def list_sessions(self, user_id: str = None) -> List[str]:
        """List session IDs for a user if supported."""
        return []
    
    async def delete_session(self, session_id: str, user_id: str = None) -> bool:
        """Delete a session if supported."""
        return False
    
    async def chat_with_session(self, messages: List[Dict[str, str]], session_id: str = None, user_id: str = None, **kwargs) -> str:
        """Generate a chat response with session context if supported."""
        # Fallback to regular chat for clients that don't support sessions
        return await self.chat(messages, **kwargs)