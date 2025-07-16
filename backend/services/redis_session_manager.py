"""
Redis-based session management for LLM conversations.
Provides short-term memory storage for conversation contexts.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

import redis
from core.config import settings

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Redis-based session management for conversation contexts."""
    
    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        """
        Initialize Redis session manager.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live for sessions in seconds (1 hour)
        """
        self.redis_url = redis_url or settings.redis_url
        self.default_ttl = default_ttl
        self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        self.session_prefix = "session:"
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info("Redis session manager connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def create_session(self, user_id: str = None) -> str:
        """
        Create a new conversation session.
        
        Args:
            user_id: Optional user ID to associate with session
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session_key = f"{self.session_prefix}{session_id}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "messages": [],
            "context": {},
            "metadata": {}
        }
        
        try:
            self.redis_client.setex(
                session_key,
                self.default_ttl,
                json.dumps(session_data)
            )
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            session_data = self.redis_client.get(session_key)
            if session_data:
                data = json.loads(session_data)
                # Update last accessed time
                data["last_accessed"] = datetime.utcnow().isoformat()
                self.redis_client.setex(session_key, self.default_ttl, json.dumps(data))
                return data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            updates: Updates to apply
            
        Returns:
            Success status
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            # Apply updates
            session_data.update(updates)
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            
            self.redis_client.setex(
                session_key,
                self.default_ttl,
                json.dumps(session_data)
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Add a message to the session conversation history.
        
        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            Success status
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        session_data["messages"].append(message)
        return self.update_session(session_id, {"messages": session_data["messages"]})
    
    def get_conversation_history(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return []
        
        messages = session_data.get("messages", [])
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def set_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """
        Set context data for a session.
        
        Args:
            session_id: Session ID
            context: Context data
            
        Returns:
            Success status
        """
        return self.update_session(session_id, {"context": context})
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get context data for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Context data
        """
        session_data = self.get_session(session_id)
        if session_data:
            return session_data.get("context", {})
        return {}
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Success status
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        try:
            result = self.redis_client.delete(session_key)
            logger.info(f"Deleted session {session_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def extend_session_ttl(self, session_id: str, ttl: int = None) -> bool:
        """
        Extend session time-to-live.
        
        Args:
            session_id: Session ID
            ttl: New TTL in seconds (uses default if not provided)
            
        Returns:
            Success status
        """
        session_key = f"{self.session_prefix}{session_id}"
        ttl = ttl or self.default_ttl
        
        try:
            result = self.redis_client.expire(session_key, ttl)
            return result
            
        except Exception as e:
            logger.error(f"Failed to extend TTL for session {session_id}: {e}")
            return False
    
    def list_user_sessions(self, user_id: str) -> List[str]:
        """
        List all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of session IDs
        """
        try:
            session_keys = self.redis_client.keys(f"{self.session_prefix}*")
            user_sessions = []
            
            for key in session_keys:
                try:
                    session_data = json.loads(self.redis_client.get(key))
                    if session_data.get("user_id") == user_id:
                        user_sessions.append(session_data["session_id"])
                except Exception:
                    continue
            
            return user_sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            # Redis automatically handles TTL expiration, but we can clean up manually
            session_keys = self.redis_client.keys(f"{self.session_prefix}*")
            cleaned_count = 0
            
            for key in session_keys:
                try:
                    session_data = json.loads(self.redis_client.get(key))
                    last_accessed = datetime.fromisoformat(session_data["last_accessed"])
                    
                    # Clean up sessions older than 24 hours
                    if datetime.utcnow() - last_accessed > timedelta(hours=24):
                        self.redis_client.delete(key)
                        cleaned_count += 1
                        
                except Exception:
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active sessions.
        
        Returns:
            Session statistics
        """
        try:
            session_keys = self.redis_client.keys(f"{self.session_prefix}*")
            total_sessions = len(session_keys)
            
            active_sessions = 0
            users_with_sessions = set()
            
            for key in session_keys:
                try:
                    session_data = json.loads(self.redis_client.get(key))
                    last_accessed = datetime.fromisoformat(session_data["last_accessed"])
                    
                    # Consider sessions accessed in last hour as active
                    if datetime.utcnow() - last_accessed < timedelta(hours=1):
                        active_sessions += 1
                    
                    if session_data.get("user_id"):
                        users_with_sessions.add(session_data["user_id"])
                        
                except Exception:
                    continue
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "unique_users": len(users_with_sessions),
                "redis_memory_usage": self.redis_client.memory_usage(f"{self.session_prefix}*") if hasattr(self.redis_client, 'memory_usage') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis session manager health."""
        try:
            # Test Redis connection
            self.redis_client.ping()
            
            # Get basic stats
            stats = self.get_session_stats()
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "session_stats": stats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "error": str(e)
            }