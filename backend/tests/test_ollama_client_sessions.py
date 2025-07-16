"""Tests for OllamaClient session management."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.llm.ollama_client import OllamaClient


class TestOllamaClientSessions:
    """Test cases for OllamaClient session management."""
    
    @pytest.fixture
    def mock_ollama_service(self):
        """Mock OllamaService."""
        with patch('services.llm.ollama_client.OllamaService') as mock_service:
            mock_instance = Mock()
            mock_instance.generate_completion = AsyncMock()
            mock_instance.health_check = AsyncMock()
            mock_service.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock RedisSessionManager."""
        with patch('services.llm.ollama_client.RedisSessionManager') as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def ollama_client(self, mock_ollama_service, mock_session_manager):
        """Create OllamaClient instance with mocked dependencies."""
        client = OllamaClient()
        return client
    
    def test_init(self, ollama_client, mock_ollama_service, mock_session_manager):
        """Test OllamaClient initialization with session support."""
        assert ollama_client.service == mock_ollama_service
        assert ollama_client.session_manager == mock_session_manager
        assert ollama_client._supports_sessions is True
    
    def test_create_session(self, ollama_client, mock_session_manager):
        """Test creating a new conversation session."""
        mock_session_manager.create_session.return_value = "session_123"
        
        session_id = ollama_client.create_session(user_id="user_456")
        
        assert session_id == "session_123"
        mock_session_manager.create_session.assert_called_once_with(user_id="user_456")
    
    @pytest.mark.asyncio
    async def test_chat_with_session(self, ollama_client, mock_ollama_service, mock_session_manager):
        """Test chat with session management."""
        # Mock conversation history
        mock_session_manager.get_conversation_history.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        # Mock LLM response
        mock_ollama_service.generate_completion.return_value = {
            "success": True,
            "response": "How can I help you today?"
        }
        
        response = await ollama_client.chat_with_session(
            session_id="session_123",
            message="What can you do?",
            user_id="user_456"
        )
        
        assert response == "How can I help you today?"
        
        # Verify session interactions
        mock_session_manager.get_conversation_history.assert_called_once_with("session_123", limit=10)
        assert mock_session_manager.add_message.call_count == 2  # user message + assistant response
        
        # Verify user message was added
        user_message_call = mock_session_manager.add_message.call_args_list[0]
        assert user_message_call[0] == ("session_123", "user", "What can you do?")
        
        # Verify assistant response was added  
        assistant_message_call = mock_session_manager.add_message.call_args_list[1]
        assert assistant_message_call[0] == ("session_123", "assistant", "How can I help you today?")
    
    @pytest.mark.asyncio
    async def test_chat_with_session_with_system_prompt(self, ollama_client, mock_ollama_service, mock_session_manager):
        """Test chat with session including system prompt."""
        mock_session_manager.get_conversation_history.return_value = []
        mock_ollama_service.generate_completion.return_value = {
            "success": True,
            "response": "I am a helpful assistant."
        }
        
        response = await ollama_client.chat_with_session(
            session_id="session_123",
            message="Who are you?",
            system_prompt="You are a helpful AI assistant."
        )
        
        assert response == "I am a helpful assistant."
        
        # Verify generate_completion was called with system prompt
        call_args = mock_ollama_service.generate_completion.call_args
        assert "You are a helpful AI assistant." in call_args[0][1]  # system_prompt parameter
    
    def test_get_session_history(self, ollama_client, mock_session_manager):
        """Test getting session conversation history."""
        expected_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        mock_session_manager.get_conversation_history.return_value = expected_history
        
        history = ollama_client.get_session_history("session_123", limit=5)
        
        assert history == expected_history
        mock_session_manager.get_conversation_history.assert_called_once_with("session_123", limit=5)
    
    def test_delete_session(self, ollama_client, mock_session_manager):
        """Test deleting a conversation session."""
        mock_session_manager.delete_session.return_value = True
        
        result = ollama_client.delete_session("session_123")
        
        assert result is True
        mock_session_manager.delete_session.assert_called_once_with("session_123")
    
    def test_set_session_context(self, ollama_client, mock_session_manager):
        """Test setting session context."""
        context = {"user_preference": "concise", "topic": "programming"}
        mock_session_manager.set_context.return_value = True
        
        result = ollama_client.set_session_context("session_123", context)
        
        assert result is True
        mock_session_manager.set_context.assert_called_once_with("session_123", context)
    
    def test_get_session_context(self, ollama_client, mock_session_manager):
        """Test getting session context."""
        expected_context = {"user_preference": "detailed", "language": "python"}
        mock_session_manager.get_context.return_value = expected_context
        
        context = ollama_client.get_session_context("session_123")
        
        assert context == expected_context
        mock_session_manager.get_context.assert_called_once_with("session_123")
    
    @pytest.mark.asyncio
    async def test_health_check_with_sessions(self, ollama_client, mock_ollama_service, mock_session_manager):
        """Test health check including session manager."""
        mock_ollama_service.health_check.return_value = {"status": "healthy", "model": "llama2"}
        mock_session_manager.health_check.return_value = {"status": "healthy", "redis_connected": True}
        
        health = await ollama_client.health_check()
        
        assert health["supports_sessions"] is True
        assert "ollama" in health
        assert "sessions" in health
        assert health["ollama"]["status"] == "healthy"
        assert health["sessions"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_generate_basic(self, ollama_client, mock_ollama_service):
        """Test basic generate method (non-session)."""
        mock_ollama_service.generate_completion.return_value = {
            "success": True,
            "response": "Generated response"
        }
        
        response = await ollama_client.generate("Test prompt")
        
        assert response == "Generated response"
        mock_ollama_service.generate_completion.assert_called_once_with("Test prompt", None)
    
    @pytest.mark.asyncio
    async def test_generate_with_error(self, ollama_client, mock_ollama_service):
        """Test generate method with error response."""
        mock_ollama_service.generate_completion.return_value = {
            "success": False,
            "error": "Model not available"
        }
        
        with pytest.raises(RuntimeError, match="Ollama generation failed: Model not available"):
            await ollama_client.generate("Test prompt")