"""Client for external LLM providers - supports Ollama and Google Generative AI."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, List
from enum import Enum
from abc import ABC, abstractmethod

import httpx
import json
import time
from datetime import datetime
from dataclasses import dataclass
from services.ollama_service import OllamaService
from core.config import settings
LOGGER = logging.getLogger(__name__)


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
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        event_data = {
            "author": self.author,
            "invocationId": self.invocation_id,
            "timestamp": self.timestamp
        }
        if self.content:
            event_data["content"] = self.content
        if self.metadata:
            event_data["metadata"] = self.metadata
        return event_data


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    GOOGLE_GENERATIVE_AI = "google_generative_ai"
    VERTEX_AI = "vertex_ai"
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
    
    # Session management methods (optional, only implemented by clients that support it)
    async def create_session(self, user_id: str, **kwargs) -> Optional[str]:
        """Create a new session for the user. Returns session ID if supported."""
        return None
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Any]:
        """Get session details if supported."""
        return None
    
    async def list_sessions(self, user_id: str) -> List[str]:
        """List session IDs for a user if supported."""
        return []
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session if supported."""
        return False
    
    async def chat_with_session(self, messages: List[Dict[str, str]], session_id: str, user_id: str, **kwargs) -> str:
        """Generate a chat response with session context if supported."""
        # Fallback to regular chat for clients that don't support sessions
        return await self.chat(messages, **kwargs)


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


class VertexAIClient(BaseLLMClient):
    """Google Vertex AI Agent Engine client with session management.
    
    This client implements proper session-based conversations using Vertex AI Agent Engine.
    Key features:
    - Session creation, management, and cleanup
    - Event tracking for conversation history
    - Proper integration with Agent Engine query endpoints
    - Fallback to stateless generation when needed
    
    Implementation follows Google's recommended practices for Agent Engine Sessions:
    - Uses session-based queries for persistent conversations
    - Maintains event history for context
    - Handles authentication with proper token caching
    - Provides both session-based and stateless operation modes
    """
    
    def __init__(self):
        self.project_id = settings.vertex_ai_project_id
        self.location = settings.vertex_ai_location
        self.agent_engine_id = settings.vertex_ai_agent_engine_id
        self.model = settings.vertex_ai_model
        self.timeout = settings.vertex_ai_timeout
        
        if not self.project_id:
            raise RuntimeError("VERTEX_AI_PROJECT_ID not configured in settings")
        if not self.agent_engine_id:
            raise RuntimeError("VERTEX_AI_AGENT_ENGINE_ID not configured in settings")
        
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1beta1"
        self.sessions_url = f"{self.base_url}/projects/{self.project_id}/locations/{self.location}/reasoningEngines/{self.agent_engine_id}/sessions"
        
        # Setup authentication
        self._setup_auth()
    
    def _setup_auth(self):
        """Setup Google Cloud authentication."""
        import os
        if settings.google_application_credentials:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
    
    async def _get_access_token(self) -> str:
        """Get Google Cloud access token for authentication."""
        try:
            # Try to use gcloud auth if available
            import subprocess
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                LOGGER.warning(f"gcloud auth failed: {result.stderr}")
        except Exception as e:
            LOGGER.warning(f"Could not get gcloud access token: {e}")
        
        # Fallback to Google Auth library
        try:
            from google.auth import default
            from google.auth.transport.requests import Request
            credentials, _ = default()
            credentials.refresh(Request())
            return credentials.token
        except Exception as e:
            raise RuntimeError(f"Could not obtain Google Cloud access token: {e}")
    
    async def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Vertex AI API."""
        access_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, timeout=self.timeout)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data, timeout=self.timeout)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200 or response.status_code == 201:
                    return response.json() if response.content else {}
                else:
                    error_msg = f"Vertex AI API error: {response.status_code} - {response.text}"
                    LOGGER.error(error_msg)
                    raise RuntimeError(error_msg)
                    
            except httpx.TimeoutException:
                raise RuntimeError("Vertex AI request timed out")
            except Exception as e:
                if not isinstance(e, RuntimeError):
                    LOGGER.error(f"Vertex AI error: {e}")
                    raise RuntimeError(f"Vertex AI error: {str(e)}")
                raise
    
    async def create_session(self, user_id: str, **kwargs) -> str:
        """Create a new Vertex AI session."""
        data = {"userId": user_id}
        
        # Add initial state if provided
        if "initial_state" in kwargs:
            data["state"] = kwargs["initial_state"]
        
        response = await self._make_request("POST", self.sessions_url, data)
        
        # Extract session ID from the operation response
        if "name" in response:
            session_id = response["name"].split("/")[-1]
            LOGGER.info(f"Created Vertex AI session {session_id} for user {user_id}")
            return session_id
        else:
            raise RuntimeError("Failed to create Vertex AI session - no session ID returned")
    
    async def get_session(self, session_id: str, user_id: str) -> VertexSession:
        """Get a Vertex AI session."""
        session_url = f"{self.sessions_url}/{session_id}"
        response = await self._make_request("GET", session_url)
        return VertexSession.from_dict(response)
    
    async def list_sessions(self, user_id: str) -> List[str]:
        """List all sessions for a user."""
        response = await self._make_request("GET", self.sessions_url)
        sessions = response.get("sessions", [])
        
        # Filter sessions by user_id and extract session IDs
        user_sessions = [
            session["name"].split("/")[-1] 
            for session in sessions 
            if session.get("userId") == user_id
        ]
        
        return user_sessions
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a Vertex AI session."""
        session_url = f"{self.sessions_url}/{session_id}"
        try:
            await self._make_request("DELETE", session_url)
            LOGGER.info(f"Deleted Vertex AI session {session_id} for user {user_id}")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def append_event(self, session_id: str, event: VertexEvent) -> bool:
        """Append an event to a session."""
        # Use the correct endpoint format from the API documentation
        event_url = f"{self.sessions_url}/{session_id}:appendEvent"
        try:
            await self._make_request("POST", event_url, event.to_dict())
            return True
        except Exception as e:
            LOGGER.error(f"Failed to append event to session {session_id}: {e}")
            return False
    
    async def list_events(self, session_id: str) -> List[Dict[str, Any]]:
        """List events in a session."""
        events_url = f"{self.sessions_url}/{session_id}/events"
        response = await self._make_request("GET", events_url)
        return response.get("events", [])
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response using Vertex AI.
        
        Note: For session-based interactions, use chat_with_session instead.
        This method creates a temporary session for stateless requests.
        """
        # Create a temporary session for this request
        temp_user_id = kwargs.get("user_id", "temp_user")
        temp_session_id = await self.create_session(temp_user_id)
        
        try:
            # Use session-based chat
            messages = [{"role": "user", "content": prompt}]
            system_prompt = kwargs.get("system_prompt")
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            response = await self.chat_with_session(
                messages=messages,
                session_id=temp_session_id,
                user_id=temp_user_id,
                **kwargs
            )
            
            return response
            
        finally:
            # Clean up temporary session
            try:
                await self.delete_session(temp_session_id, temp_user_id)
            except Exception as e:
                LOGGER.warning(f"Failed to delete temporary session {temp_session_id}: {e}")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response using Vertex AI.
        
        For persistent conversations, use chat_with_session instead.
        """
        # Use generate which creates a temporary session
        prompt_parts = []
        system_prompt = None
        
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
    
    async def _stateless_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Fallback method for stateless chat using Generative AI API directly."""
        access_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Use Vertex AI Generative AI API for stateless requests
        model_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model}:generateContent"
        
        # Convert messages to Vertex AI format
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
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
                "temperature": kwargs.get("temperature", settings.vertex_ai_temperature),
                "topK": kwargs.get("top_k", settings.vertex_ai_top_k),
                "topP": kwargs.get("top_p", settings.vertex_ai_top_p),
                "maxOutputTokens": kwargs.get("max_tokens", settings.vertex_ai_max_tokens),
            }
        }
        
        if system_instruction:
            data["systemInstruction"] = system_instruction
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    model_url,
                    headers=headers,
                    json=data,
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
                    error_msg = f"Vertex AI API error: {response.status_code} - {response.text}"
                    LOGGER.error(error_msg)
                    raise RuntimeError(error_msg)
                    
            except httpx.TimeoutException:
                raise RuntimeError("Vertex AI request timed out")
            except Exception as e:
                if not isinstance(e, RuntimeError):
                    LOGGER.error(f"Vertex AI error: {e}")
                    raise RuntimeError(f"Vertex AI error: {str(e)}")
                raise
    
    async def chat_with_session(self, messages: List[Dict[str, str]], session_id: str, user_id: str, **kwargs) -> str:
        """Generate a chat response with session context using Agent Engine.
        
        This method properly integrates with Vertex AI Agent Engine for session-based
        conversations with full context persistence.
        """
        try:
            # Verify session exists or create it
            try:
                session = await self.get_session(session_id, user_id)
            except Exception as e:
                LOGGER.info(f"Session {session_id} not found, creating new session: {e}")
                session_id = await self.create_session(user_id)
            
            # Query the Agent Engine with session context
            # Note: The :query endpoint might need adjustment based on the final API spec
            # Alternative endpoints to try: :streamQuery, :process, or :execute
            query_url = f"{self.sessions_url}/{session_id}:query"
            
            # Prepare the query request with conversation history
            # This format aligns with ADK runner's expected input structure
            query_data = {
                "query": {
                    "input": messages[-1].get("content", "") if messages else "",
                    "parameters": {
                        "temperature": kwargs.get("temperature", settings.vertex_ai_temperature),
                        "topK": kwargs.get("top_k", settings.vertex_ai_top_k),
                        "topP": kwargs.get("top_p", settings.vertex_ai_top_p),
                        "maxOutputTokens": kwargs.get("max_tokens", settings.vertex_ai_max_tokens),
                    }
                }
            }
            
            # Add system instructions if provided
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            if system_messages:
                query_data["systemInstruction"] = {
                    "parts": [{"text": msg.get("content", "")} for msg in system_messages]
                }
            
            # Make the query request to Agent Engine
            response_data = await self._make_request("POST", query_url, query_data)
            
            # Extract the response text
            if "output" in response_data:
                response_text = response_data["output"].get("text", "")
            elif "response" in response_data:
                response_text = response_data["response"].get("text", "")
            else:
                raise RuntimeError(f"Unexpected response format from Agent Engine: {response_data}")
            
            # Log the interaction as events for session history
            user_message = messages[-1] if messages else {"content": ""}
            user_event = VertexEvent(
                author="user",
                invocation_id=f"inv_{int(time.time() * 1000)}",
                timestamp=time.time(),
                content=user_message.get("content", ""),
                metadata={"role": "user", "message_index": len(messages) - 1}
            )
            
            assistant_event = VertexEvent(
                author="assistant",
                invocation_id=f"inv_{int(time.time() * 1000) + 1}",
                timestamp=time.time(),
                content=response_text,
                metadata={"role": "assistant", "response_to": user_event.invocation_id}
            )
            
            # Append events to maintain conversation history
            await self.append_event(session_id, user_event)
            await self.append_event(session_id, assistant_event)
            
            return response_text
            
        except Exception as e:
            LOGGER.error(f"Session-based chat failed: {e}", exc_info=True)
            # Only fall back to stateless if it's not a session-specific error
            if "session" not in str(e).lower():
                LOGGER.warning("Falling back to stateless chat")
                return await self._stateless_chat(messages, **kwargs)
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Vertex AI service health."""
        try:
            # Try to list sessions to verify connectivity and auth
            response = await self._make_request("GET", self.sessions_url)
            
            return {
                "healthy": True,
                "provider": "vertex_ai",
                "project_id": self.project_id,
                "location": self.location,
                "agent_engine_id": self.agent_engine_id,
                "model": self.model,
                "session_count": len(response.get("sessions", []))
            }
            
        except Exception as e:
            LOGGER.error(f"Vertex AI health check failed: {e}")
            return {
                "healthy": False,
                "provider": "vertex_ai",
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
        elif provider == LLMProvider.VERTEX_AI:
            return VertexAIClient()
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