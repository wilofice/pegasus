"""Tests for RedisSessionManager."""

import pytest
import json
from unittest.mock import Mock, patch
from services.redis_session_manager import RedisSessionManager


class TestRedisSessionManager:
    """Test cases for RedisSessionManager."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('services.redis_session_manager.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_class.from_url.return_value = mock_redis_instance
            yield mock_redis_instance
    
    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create RedisSessionManager instance with mocked Redis."""
        with patch('services.redis_session_manager.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"
            
            manager = RedisSessionManager()
            return manager
    
    def test_init(self, session_manager, mock_redis):
        """Test RedisSessionManager initialization."""
        assert session_manager.redis_client == mock_redis
        assert session_manager.default_ttl == 3600
        assert session_manager.session_prefix == "session:"
        mock_redis.ping.assert_called_once()
    
    def test_create_session(self, session_manager, mock_redis):
        """Test creating a new session."""
        session_id = session_manager.create_session(user_id="user_123")
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID length
        
        # Verify Redis setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"session:{session_id}"
        assert call_args[0][1] == 3600  # TTL
        
        # Verify session data
        session_data = json.loads(call_args[0][2])
        assert session_data["session_id"] == session_id
        assert session_data["user_id"] == "user_123"
        assert session_data["messages"] == []
    
    def test_get_session(self, session_manager, mock_redis):
        """Test getting session data."""
        session_data = {
            "session_id": "test_session",
            "user_id": "user_123",
            "messages": [],
            "context": {},
            "created_at": "2023-01-01T00:00:00.000000",
            "last_accessed": "2023-01-01T00:00:00.000000"
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        result = session_manager.get_session("test_session")
        
        assert result is not None
        assert result["session_id"] == "test_session"
        assert result["user_id"] == "user_123"
        
        # Verify last_accessed was updated
        mock_redis.setex.assert_called_once()
    
    def test_get_session_not_found(self, session_manager, mock_redis):
        """Test getting non-existent session."""
        mock_redis.get.return_value = None
        
        result = session_manager.get_session("nonexistent")
        
        assert result is None
    
    def test_add_message(self, session_manager, mock_redis):
        """Test adding message to session."""
        session_data = {
            "session_id": "test_session",
            "user_id": "user_123",
            "messages": [],
            "context": {},
            "created_at": "2023-01-01T00:00:00.000000",
            "last_accessed": "2023-01-01T00:00:00.000000"
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        result = session_manager.add_message(
            "test_session",
            "user",
            "Hello, world!",
            {"source": "test"}
        )
        
        assert result is True
        
        # Verify message was added and session updated
        assert mock_redis.setex.call_count >= 2  # get_session + update_session
    
    def test_get_conversation_history(self, session_manager, mock_redis):
        """Test getting conversation history."""
        messages = [
            {"role": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00.000000"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T00:01:00.000000"}
        ]
        session_data = {
            "session_id": "test_session",
            "messages": messages,
            "user_id": "user_123",
            "context": {},
            "created_at": "2023-01-01T00:00:00.000000",
            "last_accessed": "2023-01-01T00:00:00.000000"
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        result = session_manager.get_conversation_history("test_session", limit=1)
        
        assert len(result) == 1
        assert result[0]["content"] == "Hi there!"  # Should get last message due to limit
    
    def test_set_and_get_context(self, session_manager, mock_redis):
        """Test setting and getting session context."""
        session_data = {
            "session_id": "test_session",
            "user_id": "user_123", 
            "messages": [],
            "context": {},
            "created_at": "2023-01-01T00:00:00.000000",
            "last_accessed": "2023-01-01T00:00:00.000000"
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        # Test set context
        context = {"key": "value", "number": 42}
        result = session_manager.set_context("test_session", context)
        assert result is True
        
        # Test get context
        context_result = session_manager.get_context("test_session")
        assert context_result == context
    
    def test_delete_session(self, session_manager, mock_redis):
        """Test deleting a session."""
        mock_redis.delete.return_value = 1
        
        result = session_manager.delete_session("test_session")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("session:test_session")
    
    def test_extend_session_ttl(self, session_manager, mock_redis):
        """Test extending session TTL."""
        mock_redis.expire.return_value = True
        
        result = session_manager.extend_session_ttl("test_session", 7200)
        
        assert result is True
        mock_redis.expire.assert_called_once_with("session:test_session", 7200)
    
    def test_health_check_healthy(self, session_manager, mock_redis):
        """Test health check when Redis is healthy."""
        mock_redis.ping.return_value = True
        mock_redis.keys.return_value = ["session:1", "session:2"]
        mock_redis.get.side_effect = [
            json.dumps({"session_id": "1", "user_id": "user1", "last_accessed": "2023-01-01T23:30:00.000000"}),
            json.dumps({"session_id": "2", "user_id": "user2", "last_accessed": "2023-01-01T00:00:00.000000"})
        ]
        
        health = session_manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["redis_connected"] is True
        assert "session_stats" in health
    
    def test_health_check_unhealthy(self, session_manager, mock_redis):
        """Test health check when Redis is unhealthy."""
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        health = session_manager.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["redis_connected"] is False
        assert "error" in health