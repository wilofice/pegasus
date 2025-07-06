"""
Shared types and configurations for chat services.

This module contains common data structures used across chat orchestration,
prompt building, and related services to avoid circular imports.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from services.context_aggregator_v2 import AggregationStrategy
from services.context_ranker import RankingStrategy


class ConversationMode(Enum):
    """Available conversation modes."""
    STANDARD = "standard"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"


class ResponseStyle(Enum):
    """Available response styles."""
    CONCISE = "concise"
    DETAILED = "detailed"
    ACADEMIC = "academic"
    CASUAL = "casual"
    PROFESSIONAL = "professional"


@dataclass
class ChatConfig:
    """Configuration for chat orchestration."""
    # Context settings
    max_context_results: int = 15
    aggregation_strategy: AggregationStrategy = AggregationStrategy.ENSEMBLE
    ranking_strategy: RankingStrategy = RankingStrategy.ENSEMBLE
    
    # Conversation settings
    conversation_mode: ConversationMode = ConversationMode.STANDARD
    response_style: ResponseStyle = ResponseStyle.PROFESSIONAL
    include_sources: bool = True
    include_confidence: bool = False
    
    # LLM settings
    use_local_llm: bool = False
    llm_model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    
    # Plugin settings
    enable_plugins: bool = True
    plugin_timeout: float = 5.0
    
    # Performance settings
    context_timeout: float = 10.0
    total_timeout: float = 30.0


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ChatMetrics:
    """Metrics from chat processing."""
    context_retrieval_time_ms: float
    llm_generation_time_ms: float
    plugin_processing_time_ms: float
    total_processing_time_ms: float
    context_results_count: int
    top_context_score: float
    plugins_executed: List[str]
    confidence_score: Optional[float] = None


@dataclass
class ChatResponse:
    """Complete chat response with metadata."""
    response: str
    session_id: str
    config: ChatConfig
    metrics: ChatMetrics
    context_used: Optional[Any] = None  # AggregatedContext - avoiding circular import
    sources: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of chat response."""
        return {
            "response_length": len(self.response),
            "processing_time_ms": self.metrics.total_processing_time_ms,
            "context_results": self.metrics.context_results_count,
            "confidence": self.metrics.confidence_score,
            "sources_count": len(self.sources),
            "conversation_mode": self.config.conversation_mode.value,
            "aggregation_strategy": self.config.aggregation_strategy.value
        }