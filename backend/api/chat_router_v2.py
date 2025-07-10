"""Modern Chat Router V2 using Chat Orchestrator V2."""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, status, Query
from pydantic import BaseModel, Field
from core.config import settings
from services.chat_orchestrator_factory import get_default_chat_orchestrator
from services.chat_orchestrator_v2 import ChatOrchestratorV2
from services.chat_types import ChatConfig, ConversationMode, ResponseStyle, ChatResponse
from services.context_aggregator_v2 import AggregationStrategy
from services.context_ranker import RankingStrategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/v2", tags=["chat-v2"])

# Global orchestrator instance (will be initialized on first use)
_orchestrator: Optional[ChatOrchestratorV2] = None


async def get_orchestrator() -> ChatOrchestratorV2:
    """Get or create the chat orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = await get_default_chat_orchestrator()
    return _orchestrator


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="Session identifier for conversation continuity")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Configuration options
    conversation_mode: Optional[ConversationMode] = Field(None, description="Conversation mode")
    response_style: Optional[ResponseStyle] = Field(None, description="Response style")
    aggregation_strategy: Optional[AggregationStrategy] = Field(None, description="Context aggregation strategy")
    ranking_strategy: Optional[RankingStrategy] = Field(None, description="Context ranking strategy")
    
    # Advanced options
    max_context_results: Optional[int] = Field(None, description="Maximum context results", ge=1, le=50)
    include_sources: Optional[bool] = Field(None, description="Include source information")
    include_confidence: Optional[bool] = Field(None, description="Include confidence score")
    enable_plugins: Optional[bool] = Field(None, description="Enable plugin processing")
    use_local_llm: Optional[bool] = Field(None, description="Use local LLM instead of external")


class ChatResponseModel(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: str
    
    # Metadata
    conversation_mode: str
    response_style: str
    processing_time_ms: float
    context_results_count: int
    confidence_score: Optional[float] = None
    
    # Optional rich data
    sources: Optional[List[Dict[str, Any]]] = None
    suggestions: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    user_id: Optional[str]
    created_at: str
    last_updated: str
    conversation_turns: int
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response model."""
    service: str
    status: str
    dependencies: Dict[str, Any]
    sessions: Dict[str, Any]


def _auth(authorization: str | None = Header(default=None)) -> None:
    """Authentication dependency."""
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing Authorization header"
        )


@router.post("/", response_model=ChatResponseModel)
async def chat_v2(
    request: ChatRequest, 
    _: None = Depends(_auth),
    include_sources: bool = Query(default=True, description="Include source information"),
    include_metrics: bool = Query(default=False, description="Include detailed metrics")
) -> ChatResponseModel:
    """Enhanced chat endpoint with modern orchestration.
    
    This endpoint provides advanced conversational AI capabilities with:
    - Context aggregation from multiple sources
    - Intelligent ranking and relevance scoring
    - Multiple conversation modes and response styles
    - Plugin system integration
    - Session management and conversation history
    """
    try:
        request.user_id = settings.vertex_ai_user_id
        orchestrator = await get_orchestrator()
        
        # Build configuration from request
        config = ChatConfig()
        
        if request.conversation_mode:
            config.conversation_mode = request.conversation_mode
        if request.response_style:
            config.response_style = request.response_style
        if request.aggregation_strategy:
            config.aggregation_strategy = request.aggregation_strategy
        if request.ranking_strategy:
            config.ranking_strategy = request.ranking_strategy
        if request.max_context_results:
            config.max_context_results = request.max_context_results
        if request.include_sources is not None:
            config.include_sources = request.include_sources or include_sources
        if request.include_confidence is not None:
            config.include_confidence = request.include_confidence
        if request.enable_plugins is not None:
            config.enable_plugins = request.enable_plugins
        if request.use_local_llm is not None:
            config.use_local_llm = request.use_local_llm
        
        # Process chat
        chat_response = await orchestrator.chat(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            config=config
        )
        
        # Build response
        response = ChatResponseModel(
            response=chat_response.response,
            session_id=chat_response.session_id,
            conversation_mode=chat_response.config.conversation_mode.value,
            response_style=chat_response.config.response_style.value,
            processing_time_ms=chat_response.metrics.total_processing_time_ms,
            context_results_count=chat_response.metrics.context_results_count,
            confidence_score=chat_response.metrics.confidence_score
        )
        
        # Add optional data based on configuration
        if config.include_sources and chat_response.sources:
            response.sources = chat_response.sources
        
        if chat_response.suggestions:
            response.suggestions = chat_response.suggestions
        
        if include_metrics:
            response.metrics = {
                "context_retrieval_time_ms": chat_response.metrics.context_retrieval_time_ms,
                "llm_generation_time_ms": chat_response.metrics.llm_generation_time_ms,
                "plugin_processing_time_ms": chat_response.metrics.plugin_processing_time_ms,
                "plugins_executed": chat_response.metrics.plugins_executed,
                "top_context_score": chat_response.metrics.top_context_score
            }
        
        logger.info(f"Chat V2 processed successfully: {len(chat_response.response)} chars in {response.processing_time_ms:.1f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Chat V2 processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(
    session_id: str,
    _: None = Depends(_auth)
) -> SessionInfo:
    """Get information about a conversation session."""
    try:
        orchestrator = await get_orchestrator()
        session_info = orchestrator.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionInfo(**session_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session info retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session info retrieval failed: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    _: None = Depends(_auth)
) -> Dict[str, str]:
    """Clear a conversation session."""
    try:
        orchestrator = await get_orchestrator()
        cleared = orchestrator.clear_session(session_id)
        
        if not cleared:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return {"message": f"Session {session_id} cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session clearing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session clearing failed: {str(e)}"
        )


@router.delete("/sessions")
async def clear_all_sessions(_: None = Depends(_auth)) -> Dict[str, Any]:
    """Clear all conversation sessions."""
    try:
        orchestrator = await get_orchestrator()
        count = orchestrator.clear_all_sessions()
        
        return {
            "message": f"Cleared {count} sessions successfully",
            "sessions_cleared": count
        }
        
    except Exception as e:
        logger.error(f"All sessions clearing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sessions clearing failed: {str(e)}"
        )


@router.get("/modes")
async def get_conversation_modes() -> Dict[str, List[str]]:
    """Get available conversation modes and response styles."""
    return {
        "conversation_modes": [mode.value for mode in ConversationMode],
        "response_styles": [style.value for style in ResponseStyle],
        "aggregation_strategies": [strategy.value for strategy in AggregationStrategy],
        "ranking_strategies": [strategy.value for strategy in RankingStrategy]
    }


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health of chat orchestrator and dependencies."""
    try:
        orchestrator = await get_orchestrator()
        health = await orchestrator.health_check()
        
        return HealthResponse(**health)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/config")
async def get_default_config() -> Dict[str, Any]:
    """Get default chat configuration."""
    try:
        config = ChatConfig()
        return {
            "max_context_results": config.max_context_results,
            "aggregation_strategy": config.aggregation_strategy.value,
            "ranking_strategy": config.ranking_strategy.value,
            "conversation_mode": config.conversation_mode.value,
            "response_style": config.response_style.value,
            "include_sources": config.include_sources,
            "include_confidence": config.include_confidence,
            "enable_plugins": config.enable_plugins,
            "use_local_llm": config.use_local_llm,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
    except Exception as e:
        logger.error(f"Config retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Config retrieval failed: {str(e)}"
        )