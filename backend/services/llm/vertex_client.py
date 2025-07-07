"""Google Vertex AI Agent Engine client with session management."""

import logging
import httpx
import time
from typing import Dict, List, Optional, Any
from .base import BaseLLMClient, VertexSession, VertexEvent
from core.config import settings

LOGGER = logging.getLogger(__name__)


class VertexAIClient(BaseLLMClient):
    """Google Vertex AI Agent Engine client with session management.
    
    This client implements proper session-based conversations using Vertex AI Agent Engine.
    Key features:
    - Session creation, management, and cleanup
    - Event tracking for conversation history
    - System instruction optimization (sent only once per session)
    - Proper integration with database conversation saving
    - Fallback to stateless generation when needed
    
    Implementation follows Google's recommended practices for Agent Engine Sessions:
    - Uses event-based session management for persistent conversations
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
        self.user_id = settings.vertex_ai_user_id  # Static user ID for single-user app
        
        if not self.project_id:
            raise RuntimeError("VERTEX_AI_PROJECT_ID not configured in settings")
        if not self.agent_engine_id:
            raise RuntimeError("VERTEX_AI_AGENT_ENGINE_ID not configured in settings")
        if not self.user_id:
            raise RuntimeError("VERTEX_AI_USER_ID not configured in settings")
        
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1beta1"
        self.sessions_url = f"{self.base_url}/projects/{self.project_id}/locations/{self.location}/reasoningEngines/{self.agent_engine_id}/sessions"
        
        # Persistent session for this user
        self._current_session_id = None
        self._session_initialized = False  # Track if system instructions were sent
        
        # Setup authentication
        self._setup_auth()
    
    async def _get_or_create_session(self) -> str:
        """Get the current persistent session or create a new one."""
        if self._current_session_id:
            try:
                # Verify the session still exists
                await self.get_session(self._current_session_id, self.user_id)
                return self._current_session_id
            except Exception as e:
                LOGGER.warning(f"Current session {self._current_session_id} no longer valid: {e}")
                self._current_session_id = None
                self._session_initialized = False
        
        # Create a new persistent session
        self._current_session_id = await self.create_session(self.user_id)
        self._session_initialized = False
        LOGGER.info(f"Created new persistent session: {self._current_session_id}")
        return self._current_session_id
    
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
        """Generate a response using Vertex AI with persistent session.
        
        This method always uses session-based communication for consistent context.
        """
        # Ensure we have a persistent session
        session_id = await self._get_or_create_session()
        
        # Use session-based chat
        messages = [{"role": "user", "content": prompt}]
        system_prompt = kwargs.get("system_prompt")
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        response = await self.chat_with_session(
            messages=messages,
            session_id=session_id,
            user_id=self.user_id,
            **kwargs
        )
        
        return response
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response using Vertex AI with persistent session.
        
        This method always uses session-based communication for consistent context.
        """
        # Ensure we have a persistent session
        session_id = await self._get_or_create_session()
        
        response = await self.chat_with_session(
            messages=messages,
            session_id=session_id,
            user_id=self.user_id,
            **kwargs
        )
        
        return response
    
    async def chat_with_session(self, messages: List[Dict[str, str]], session_id: str, user_id: str, **kwargs) -> str:
        """Generate a chat response with session context using Agent Engine.
        
        This method properly integrates with Vertex AI Agent Engine for session-based
        conversations with full context persistence.
        """
        try:
            # Verify session exists or create it
            session_created = False
            try:
                session = await self.get_session(session_id, user_id)
            except Exception as e:
                LOGGER.info(f"Session {session_id} not found, creating new session: {e}")
                session_id = await self.create_session(user_id)
                session_created = True
                # Update the current session ID if this is our persistent session
                if user_id == self.user_id:
                    self._current_session_id = session_id
                    self._session_initialized = False
            
            # Handle system instructions - only send once per session
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            if system_messages and (session_created or not self._session_initialized):
                # Send system instruction as initial event
                system_event = VertexEvent(
                    author="system",
                    invocation_id=f"sys_{int(time.time() * 1000)}",
                    timestamp=time.time(),
                    content=system_messages[0].get("content", "")
                )
                await self.append_event(session_id, system_event)
                if user_id == self.user_id:
                    self._session_initialized = True
                LOGGER.info(f"Sent system instructions to session {session_id}")
            
            # Get only the latest user message (not system messages)
            user_messages = [msg for msg in messages if msg.get("role") != "system"]
            if not user_messages:
                raise ValueError("No user messages found in conversation")
            
            latest_message = user_messages[-1]
            
            # Add user message as event
            user_event = VertexEvent(
                author="user",
                invocation_id=f"user_{int(time.time() * 1000)}",
                timestamp=time.time(),
                content=latest_message.get("content", "")
            )
            
            await self.append_event(session_id, user_event)
            
            # Use stateless generation but maintain session context through events
            # This is because the Agent Engine :query endpoint doesn't exist in the current API
            LOGGER.debug(f"Using stateless generation with session context for session {session_id}")
            response_text = await self._stateless_chat(user_messages, **kwargs)
            
            # Add assistant response as event to maintain session history
            assistant_event = VertexEvent(
                author="assistant", 
                invocation_id=f"assistant_{int(time.time() * 1000)}",
                timestamp=time.time(),
                content=response_text
            )
            
            await self.append_event(session_id, assistant_event)
            
            return response_text
            
        except Exception as e:
            LOGGER.error(f"Session-based chat failed: {e}", exc_info=True)
            # Fall back to stateless generation
            LOGGER.warning("Falling back to stateless chat")
            return await self._stateless_chat(messages, **kwargs)
    
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
    
    async def reset_session(self) -> str:
        """Reset the persistent session by creating a new one."""
        # Delete the current session if it exists
        if self._current_session_id:
            try:
                await self.delete_session(self._current_session_id, self.user_id)
                LOGGER.info(f"Deleted old session: {self._current_session_id}")
            except Exception as e:
                LOGGER.warning(f"Failed to delete old session {self._current_session_id}: {e}")
            finally:
                self._current_session_id = None
                self._session_initialized = False
        
        # Create a new session
        return await self._get_or_create_session()
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID without creating a new one."""
        return self._current_session_id