"""Tests for QdrantManager."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.qdrant_manager import QdrantManager


class TestQdrantManager:
    """Test cases for QdrantManager."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client."""
        with patch('services.qdrant_manager.QdrantClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer."""
        with patch('services.qdrant_manager.SentenceTransformer') as mock_transformer:
            mock_instance = Mock()
            mock_instance.get_sentence_embedding_dimension.return_value = 384
            mock_instance.encode.return_value = [[0.1] * 384, [0.2] * 384]
            mock_transformer.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def qdrant_manager(self, mock_qdrant_client, mock_sentence_transformer):
        """Create QdrantManager instance with mocked dependencies."""
        with patch('services.qdrant_manager.settings') as mock_settings:
            mock_settings.qdrant_host = "localhost"
            mock_settings.qdrant_port = 6333
            mock_settings.qdrant_collection_name = "test_collection"
            mock_settings.embedding_model = "all-MiniLM-L6-v2"
            
            manager = QdrantManager()
            return manager
    
    def test_init(self, qdrant_manager, mock_qdrant_client, mock_sentence_transformer):
        """Test QdrantManager initialization."""
        assert qdrant_manager.client == mock_qdrant_client
        assert qdrant_manager.embedding_model == mock_sentence_transformer
        assert qdrant_manager.vector_size == 384
        mock_qdrant_client.get_collections.assert_called_once()
    
    def test_add_chunks(self, qdrant_manager, mock_qdrant_client, mock_sentence_transformer):
        """Test adding chunks to Qdrant."""
        chunks = [
            {
                "text": "Test chunk 1",
                "audio_id": "audio_1",
                "user_id": "user_1"
            },
            {
                "text": "Test chunk 2", 
                "audio_id": "audio_2",
                "user_id": "user_2"
            }
        ]
        
        mock_sentence_transformer.encode.return_value = [[0.1] * 384, [0.2] * 384]
        
        result = qdrant_manager.add_chunks(chunks)
        
        assert len(result) == 2
        mock_qdrant_client.upsert.assert_called_once()
        mock_sentence_transformer.encode.assert_called_once_with(['Test chunk 1', 'Test chunk 2'])
    
    def test_search_chunks(self, qdrant_manager, mock_qdrant_client, mock_sentence_transformer):
        """Test searching chunks in Qdrant."""
        # Mock search results
        mock_result = Mock()
        mock_result.id = "chunk_1"
        mock_result.score = 0.95
        mock_result.payload = {
            "text": "Test chunk",
            "audio_id": "audio_1",
            "user_id": "user_1"
        }
        mock_qdrant_client.search.return_value = [mock_result]
        
        # Mock embedding
        mock_sentence_transformer.encode.return_value = [0.1] * 384
        
        results = qdrant_manager.search_chunks("test query", user_id="user_1", limit=5)
        
        assert len(results) == 1
        assert results[0]["id"] == "chunk_1"
        assert results[0]["score"] == 0.95
        assert results[0]["text"] == "Test chunk"
        
        mock_qdrant_client.search.assert_called_once()
        mock_sentence_transformer.encode.assert_called_once_with("test query")
    
    def test_get_chunk_by_id(self, qdrant_manager, mock_qdrant_client):
        """Test getting chunk by ID."""
        # Mock retrieve result
        mock_point = Mock()
        mock_point.id = "chunk_1"
        mock_point.payload = {"text": "Test chunk", "audio_id": "audio_1"}
        mock_qdrant_client.retrieve.return_value = [mock_point]
        
        result = qdrant_manager.get_chunk_by_id("chunk_1")
        
        assert result["id"] == "chunk_1"
        assert result["text"] == "Test chunk"
        mock_qdrant_client.retrieve.assert_called_once_with(
            collection_name="test_collection",
            ids=["chunk_1"]
        )
    
    def test_delete_chunks(self, qdrant_manager, mock_qdrant_client):
        """Test deleting chunks."""
        chunk_ids = ["chunk_1", "chunk_2"]
        
        result = qdrant_manager.delete_chunks(chunk_ids)
        
        assert result is True
        mock_qdrant_client.delete.assert_called_once_with(
            collection_name="test_collection",
            points_selector=chunk_ids
        )
    
    def test_get_collection_stats(self, qdrant_manager, mock_qdrant_client):
        """Test getting collection statistics."""
        # Mock collection info
        mock_info = Mock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.status = "green"
        mock_qdrant_client.get_collection.return_value = mock_info
        
        stats = qdrant_manager.get_collection_stats()
        
        assert stats["vectors_count"] == 100
        assert stats["points_count"] == 100
        assert stats["status"] == "green"