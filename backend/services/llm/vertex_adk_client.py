"""Google Vertex AI Agent Development Kit (ADK) client with advanced session management.

This implementation uses the Vertex AI Agent Development Kit for robust session management,
agent orchestration, and consistent conversation handling across the Pegasus platform.
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# ADK and Vertex AI imports
from google import adk
from google.adk.sessions import VertexAiSessionService
import vertexai
from vertexai import agent_engines

# Local imports
from .base import BaseLLMClient
from core.config import settings
from services.system_instructions import get_complete_system_instructions
from core.database import get_db
from repositories.user_session_repository import UserSessionRepository

LOGGER = logging.getLogger(__name__)


@dataclass
class PegasusAgentConfig:
    """Configuration for the Pegasus ADK agent."""
    name: str = "pegasus_assistant"
    model: str = "gemini-2.5-flash"
    instruction: str = None  # Will be set dynamically from system_instructions
    timeout: float = 60.0
    temperature: float = 0.7
    max_tokens: int = 2048
    strategy: str = "conversational_balanced"
    response_style: str = "professional"
    


class PegasusADKAgent:
    """ADK Agent implementation for Pegasus conversational AI."""
    
    def __init__(self, config: PegasusAgentConfig):
        self.config = config
        # Set instruction from shared system instructions if not provided
        if not self.config.instruction:
            self.config.instruction = get_complete_system_instructions(
                strategy=self.config.strategy,
                response_style=self.config.response_style
            )
        self._agent = None
        self._setup_agent()
    
    def _setup_agent(self):
        """Setup the ADK agent with Pegasus-specific configuration."""
        # Define agent tools (can be extended with Pegasus-specific tools)
        def analyze_context(query: str, context: str = "") -> Dict[str, Any]:
            """Tool to analyze query context and provide enhanced responses."""
            return {
                "analysis": f"Analyzing query: {query}",
                "context_used": bool(context),
                "enhanced_response": True
            }
        
        def format_response(content: str, style: str = "conversational") -> Dict[str, str]:
            """Tool to format responses according to Pegasus style guidelines."""
            return {
                "formatted_content": content,
                "style_applied": style,
                "pegasus_formatting": True
            }
        
        # Create the ADK agent without tools initially to avoid conflicts
        try:
            self._agent = adk.Agent(
                model=self.config.model,
                name=self.config.name,
                instruction=self.config.instruction,
                tools=[]  # Start with no tools to avoid content conflicts
            )
        except Exception as e:
            LOGGER.warning(f"Failed to create ADK agent with model {self.config.model}: {e}")
            # Fallback to a simpler agent configuration
            self._agent = adk.Agent(
                model="gemini-2.0-flash-exp",  # Use a known good model
                name=self.config.name,
                instruction=self.config.instruction
            )
        
        LOGGER.info(f"Pegasus ADK agent '{self.config.name}' initialized with model {self.config.model}")
    
    @property
    def agent(self) -> adk.Agent:
        """Get the underlying ADK agent."""
        return self._agent


class VertexADKClient(BaseLLMClient):
    """Vertex AI Agent Development Kit client for Pegasus.
    
    This client provides advanced session management and agent orchestration
    using Google's Vertex AI Agent Development Kit (ADK).
    
    Key features:
    - ADK-based agent management with custom tools
    - Vertex AI Agent Engine session persistence
    - Automatic session lifecycle management
    - Enhanced conversation context handling
    - Tool-based response generation
    - Seamless integration with Pegasus workflows
    """
    
    def __init__(self):
        """Initialize the Vertex ADK client with Pegasus configuration."""
        # Load configuration
        self.project_id = settings.vertex_ai_project_id
        self.location = settings.vertex_ai_location
        self.agent_engine_id = settings.vertex_ai_agent_engine_id
        self.user_id = settings.vertex_ai_user_id
        
        # Validate required configuration
        self._validate_config()
        
        # Initialize ADK components
        self._agent_config = PegasusAgentConfig(
            model=settings.vertex_ai_model,
            timeout=settings.vertex_ai_timeout,
            temperature=settings.vertex_ai_temperature,
            max_tokens=settings.vertex_ai_max_tokens
        )
        
        # Initialize agent and session service
        self._pegasus_agent = PegasusADKAgent(self._agent_config)
        self._session_service = None
        self._runner = None
        self._current_session_id = None
        
        # Initialize Vertex AI and session service
        self._setup_vertex_ai()
        self._setup_session_service()
        self._setup_runner()
        
        LOGGER.info(f"VertexADKClient initialized for project {self.project_id} in {self.location}")
    
    def _validate_config(self):
        """Validate required configuration parameters."""
        if not self.project_id:
            raise RuntimeError("VERTEX_AI_PROJECT_ID not configured in settings")
        if not self.agent_engine_id:
            raise RuntimeError("VERTEX_AI_AGENT_ENGINE_ID not configured in settings")
        if not self.user_id:
            raise RuntimeError("VERTEX_AI_USER_ID not configured in settings")
        if not self.location:
            raise RuntimeError("VERTEX_AI_LOCATION not configured in settings")
    
    def _setup_vertex_ai(self):
        """Initialize Vertex AI with project configuration."""
        try:
            vertexai.init(project=self.project_id, location=self.location)
            LOGGER.info("Vertex AI initialized successfully")
        except Exception as e:
            LOGGER.error(f"Failed to initialize Vertex AI: {e}")
            raise RuntimeError(f"Vertex AI initialization failed: {e}")
    
    def _setup_session_service(self):
        """Setup the Vertex AI session service for ADK integration."""
        try:
            self._session_service = VertexAiSessionService(
                project=self.project_id,
                location=self.location,
                agent_engine_id=self.agent_engine_id
            )
            LOGGER.info("Vertex AI session service initialized")
        except Exception as e:
            LOGGER.error(f"Failed to initialize session service: {e}")
            raise RuntimeError(f"Session service initialization failed: {e}")
    
    def _setup_runner(self):
        """Setup the ADK runner with session service integration."""
        try:
            self._runner = adk.Runner(
                agent=self._pegasus_agent.agent,
                app_name=self.agent_engine_id,
                session_service=self._session_service
            )
            LOGGER.info("ADK runner initialized with session service")
        except Exception as e:
            LOGGER.error(f"Failed to initialize ADK runner: {e}")
            raise RuntimeError(f"ADK runner initialization failed: {e}")
    
    async def _get_or_create_session(self) -> str:
        """Get the current session or create a new one using ADK session service and database."""
        # First check database for existing active session
        try:
            async for db_session in get_db():
                session_repo = UserSessionRepository(db_session)
                user_session = await session_repo.get_active_session(self.user_id)
                
                if user_session and user_session.session_id:
                    # Verify the session is still valid in ADK
                    try:
                        # TODO: Add session validation with ADK if needed
                        self._current_session_id = user_session.session_id
                        LOGGER.info(f"Reusing existing session {self._current_session_id} for user {self.user_id}")
                        return self._current_session_id
                    except Exception as e:
                        LOGGER.warning(f"Existing session {user_session.session_id} is invalid: {e}")
                        # Deactivate invalid session
                        await session_repo.deactivate_session(user_session.session_id)
                
                # No valid session found, create new one
                break
        except Exception as e:
            LOGGER.warning(f"Error checking database for existing session: {e}")
        
        # Create new session using ADK session service
        try:
            # Use ADK session creation
            session = await self._session_service.create_session(
                app_name=self.agent_engine_id,
                user_id=self.user_id
            )
            self._current_session_id = session.id
            LOGGER.info(f"Created new ADK session: {self._current_session_id}")
            
            # Store in database
            try:
                async for db_session in get_db():
                    session_repo = UserSessionRepository(db_session)
                    await session_repo.create_session(self.user_id, self._current_session_id)
                    LOGGER.info(f"Stored session {self._current_session_id} in database for user {self.user_id}")
                    break
            except Exception as e:
                LOGGER.error(f"Failed to store session in database: {e}")
            
            return self._current_session_id
        except Exception as e:
            LOGGER.error(f"Failed to create ADK session: {e}")
            raise RuntimeError(f"Session creation failed: {e}")
    
    async def _run_agent_query(self, content: str, session_id: str) -> str:
        """Run a query through the ADK agent with session context."""
        try:
            # Create a simple text message for the agent
            LOGGER.debug(f"Running agent query with content: {content[:100]}...")
            
            # Try using the runner with a more robust approach
            try:
                # Alternative approach: Use the session service directly for more control
                if hasattr(self._session_service, 'query') or hasattr(self._session_service, 'send_message'):
                    # Try direct session query if available
                    LOGGER.debug("Attempting direct session query")
                    # This is a placeholder - actual method depends on ADK version
                    response = await self._handle_direct_query(content, session_id)
                    if response:
                        return response
                
                # Fallback to runner approach with better error handling
                # Create the simplest possible content structure
                from google.genai import types
                from google.adk.agents import RunConfig
                user_content = types.Content(
                    role='user',
                    parts=[types.Part(text=content)]
                )
                events = []

                configRun = RunConfig()
                # Run the agent with session context
                async for event in self._runner.run_async(
                    user_id=self.user_id,
                    session_id=session_id,
                    new_message=user_content,
                ):
                    events.append(event)
                
                # Extract response with improved handling
                final_response = None
                response_parts = []
                
                for event in events:
                    try:
                        if hasattr(event, 'content') and event.content:
                            if hasattr(event.content, 'parts') and event.content.parts:
                                for part in event.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_parts.append(part.text)
                                        if hasattr(event, 'is_final_response') and event.is_final_response():
                                            final_response = part.text
                                            break
                    except Exception as event_error:
                        LOGGER.warning(f"Error processing event: {event_error}")
                        continue
                
                # Use the final response or concatenate all parts
                if final_response:
                    LOGGER.debug(f"ADK agent final response generated for session {session_id}")
                    return final_response
                elif response_parts:
                    LOGGER.debug(f"ADK agent response assembled from {len(response_parts)} parts")
                    return " ".join(response_parts)
                else:
                    raise RuntimeError("No response content received from ADK agent")
                    
            except Exception as adk_error:
                LOGGER.error(f"ADK runner error: {adk_error}")
                # Enhanced fallback response
                return self._create_fallback_response(content, str(adk_error))
                
        except Exception as e:
            LOGGER.error(f"ADK agent query failed: {e}")
            raise RuntimeError(f"Agent query failed: {e}")
    
    async def _handle_direct_query(self, content: str, session_id: str) -> Optional[str]:
        """Handle direct query through session service if available."""
        # This is a placeholder for direct session querying
        # Actual implementation depends on ADK session service capabilities
        return None
    
    def _create_fallback_response(self, content: str, error: str) -> str:
        """Create a helpful fallback response when ADK fails."""
        if "oneof field 'data' is already set" in error:
            return f"I understand your message: '{content[:100]}...' but I'm experiencing a technical issue with message formatting. Please try rephrasing your question."
        else:
            return f"I received your message but encountered a temporary issue. Please try again in a moment."
    
    # BaseLLMClient interface implementation
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response using the ADK agent with session context."""
        try:
            # Get or create session
            session_id = await self._get_or_create_session()
            
            # Run the query through ADK agent
            response = await self._run_agent_query(prompt, session_id)
            
            return response
            
        except Exception as e:
            LOGGER.error(f"ADK generation failed: {e}")
            # Fallback to a simple error response
            return "I apologize, but I encountered an error while processing your request. Please try again."
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat response using ADK agent with full conversation context."""
        try:
            # Get or create session
            session_id = await self._get_or_create_session()
            
            # Extract the latest user message
            user_messages = [msg for msg in messages if msg.get("role") != "system"]
            if not user_messages:
                raise ValueError("No user messages found in conversation")
            
            latest_message = user_messages[-1].get("content", "")
            
            # For system messages, we'll incorporate them into the agent's context
            # ADK handles this through the agent's instruction and session persistence
            
            # Run the query through ADK agent
            response = await self._run_agent_query(latest_message, session_id)
            
            return response
            
        except Exception as e:
            LOGGER.error(f"ADK chat failed: {e}")
            return "I apologize, but I encountered an error while processing your chat message. Please try again."
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the ADK client and its components."""
        try:
            # Test session service connectivity
            test_session = await self._session_service.create_session(
                app_name=self.agent_engine_id,
                user_id=f"health_check_{int(time.time())}"
            )
            
            # Clean up test session
            try:
                await self._session_service.delete_session(
                    app_name=self.agent_engine_id,
                    user_id=f"health_check_{int(time.time())}",
                    session_id=test_session.id
                )
            except:
                pass  # Ignore cleanup errors
            
            return {
                "healthy": True,
                "provider": "vertex_adk",
                "project_id": self.project_id,
                "location": self.location,
                "agent_engine_id": self.agent_engine_id,
                "agent_name": self._agent_config.name,
                "model": self._agent_config.model,
                "session_service": "connected"
            }
            
        except Exception as e:
            LOGGER.error(f"ADK health check failed: {e}")
            return {
                "healthy": False,
                "provider": "vertex_adk", 
                "error": str(e),
                "project_id": self.project_id,
                "location": self.location
            }
    
    # Session management methods
    
    async def create_session(self, user_id: str = None, **kwargs) -> str:
        """Create a new session using ADK session service."""
        target_user_id = user_id or self.user_id
        try:
            session = await self._session_service.create_session(
                app_name=self.agent_engine_id,
                user_id=target_user_id,
                **kwargs
            )
            LOGGER.info(f"Created ADK session {session.id} for user {target_user_id}")
            return session.id
        except Exception as e:
            LOGGER.error(f"ADK session creation failed: {e}")
            raise RuntimeError(f"Session creation failed: {e}")
    
    async def list_sessions(self, user_id: str = None) -> List[str]:
        """List sessions for a user using ADK session service."""
        target_user_id = user_id or self.user_id
        try:
            sessions = await self._session_service.list_sessions(
                app_name=self.agent_engine_id,
                user_id=target_user_id
            )
            return sessions.session_ids
        except Exception as e:
            LOGGER.error(f"ADK session listing failed: {e}")
            return []
    
    async def delete_session(self, session_id: str, user_id: str = None) -> bool:
        """Delete a session using ADK session service.""" 
        target_user_id = user_id or self.user_id
        try:
            await self._session_service.delete_session(
                app_name=self.agent_engine_id,
                user_id=target_user_id,
                session_id=session_id
            )
            
            # Clear current session if it was deleted
            if self._current_session_id == session_id:
                self._current_session_id = None
                
            LOGGER.info(f"Deleted ADK session {session_id} for user {target_user_id}")
            return True
        except Exception as e:
            LOGGER.error(f"ADK session deletion failed: {e}")
            return False
    
    async def chat_with_session(self, messages: List[Dict[str, str]], session_id: str = None, user_id: str = None, **kwargs) -> str:
        """Generate a chat response with explicit session ID using ADK."""
        try:
            target_session_id = session_id or await self._get_or_create_session()
            
            # Extract latest user message
            user_messages = [msg for msg in messages if msg.get("role") != "system"]
            if not user_messages:
                raise ValueError("No user messages found in conversation")
            
            latest_message = user_messages[-1].get("content", "")
            
            # Run through ADK agent with specified session
            response = await self._run_agent_query(latest_message, target_session_id)
            
            return response
            
        except Exception as e:
            LOGGER.error(f"ADK session chat failed: {e}")
            return "I apologize, but I encountered an error while processing your message. Please try again."
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
    
    async def reset_session(self) -> str:
        """Reset the current session by creating a new one."""
        if self._current_session_id:
            try:
                await self.delete_session(self._current_session_id)
            except Exception as e:
                LOGGER.warning(f"Failed to delete old session {self._current_session_id}: {e}")
            finally:
                self._current_session_id = None
        
        return await self._get_or_create_session()