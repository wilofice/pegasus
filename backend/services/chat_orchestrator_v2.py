"""Modern Chat Orchestrator V2 integrating context aggregation, ranking, and LLM services."""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

from core.config import settings
from services.context_aggregator_v2 import ContextAggregatorV2, AggregatedContext, AggregationConfig
from services.context_ranker import RankingStrategy
from services.llm_client import get_llm_client
from services.intelligent_prompt_builder import get_intelligent_prompt_builder
from services.ollama_service import OllamaService
from services.plugin_manager import PluginManager
from services.chat_types import (
    ConversationMode, ResponseStyle, ChatConfig, ConversationContext, 
    ChatMetrics, ChatResponse
)
from models.conversation_history import ConversationHistory
from repositories.conversation_history_repository import ConversationHistoryRepository
from repositories.audio_repository import AudioRepository
from core.database import async_session

logger = logging.getLogger(__name__)


class ChatOrchestratorV2:
    """Modern chat orchestrator with context aggregation, ranking, and plugin integration."""
    
    def __init__(self,
                 context_aggregator: ContextAggregatorV2,
                 plugin_manager: Optional[PluginManager] = None,
                 ollama_service: Optional[OllamaService] = None,
                 default_config: Optional[ChatConfig] = None):
        self.context_aggregator = context_aggregator
        self.plugin_manager = plugin_manager
        self.ollama_service = ollama_service
        self.default_config = default_config or ChatConfig()
        
        logger.info("Chat Orchestrator V2 initialized with modern services")
    
    async def chat(self,
                   message: str,
                   session_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   config: Optional[ChatConfig] = None,
                   **kwargs) -> ChatResponse:
        start_time = datetime.now()
        config = config or self.default_config
        session_id = session_id or str(uuid.uuid4())
        
        # Track timing for different operations
        context_start = datetime.now()
        plugin_start = None
        llm_start = None
        
        async with async_session() as db:
            try:
                history_repo = ConversationHistoryRepository(db)
                
                conversation_history = await history_repo.get_recent_for_user(
                    user_id, settings.conversation_history_lookback_days
                )
                
                # Detect if this is the first request in the session
                # This can be based on conversation history being empty
                # or session being newly created in the LLM client
                is_first_request = len(conversation_history) == 0
                
                logger.debug(f"Session state detection: session_id={session_id}, history_count={len(conversation_history)}, is_first_request={is_first_request}")
                
                context = ConversationContext(
                    session_id=session_id,
                    user_id=user_id,
                    conversation_history=[h.to_dict() for h in conversation_history]
                )

                # Coordinate session state with LLM client
                await self._coordinate_llm_session(session_id, user_id, is_first_request)

                # Retrieve context
                aggregated_context = await self._retrieve_context(message, config, user_id, context, **kwargs)
                context_time = (datetime.now() - context_start).total_seconds() * 1000
                
                # Process plugins
                plugin_start = datetime.now()
                plugin_results = await self._process_plugins(message, aggregated_context, config, context)
                plugin_time = (datetime.now() - plugin_start).total_seconds() * 1000
                
                # Generate response
                llm_start = datetime.now()
                response_text = await self._generate_response(
                    message, aggregated_context, plugin_results, config, context, db, is_first_request
                )
                llm_time = (datetime.now() - llm_start).total_seconds() * 1000
                
                # Save conversation
                await self._save_and_process_conversation(
                    history_repo, session_id, user_id, message, response_text, aggregated_context
                )

                # Calculate total time
                total_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Extract metrics from aggregated context
                context_results_count = len(aggregated_context.results) if aggregated_context and aggregated_context.results else 0
                top_context_score = aggregated_context.results[0].unified_score if aggregated_context and aggregated_context.results else 0.0
                plugins_executed = plugin_results.get("executed_plugins", []) if plugin_results else []
                
                # Create metrics with all required arguments
                metrics = ChatMetrics(
                    context_retrieval_time_ms=context_time,
                    llm_generation_time_ms=llm_time,
                    plugin_processing_time_ms=plugin_time,
                    total_processing_time_ms=total_time,
                    context_results_count=context_results_count,
                    top_context_score=top_context_score,
                    plugins_executed=plugins_executed,
                    confidence_score=self._calculate_confidence(aggregated_context, plugin_results)
                )

                return ChatResponse(
                    response=response_text,
                    session_id=session_id,
                    config=config,
                    metrics=metrics,
                    context_used=aggregated_context,
                    sources=self._extract_sources(aggregated_context, config),
                    suggestions=self._generate_suggestions(message, aggregated_context, config)
                )

            except Exception as e:
                logger.error(f"Chat processing failed: {e}", exc_info=True)
                # Create minimal metrics for error case
                error_metrics = ChatMetrics(
                    context_retrieval_time_ms=0.0,
                    llm_generation_time_ms=0.0,
                    plugin_processing_time_ms=0.0,
                    total_processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    context_results_count=0,
                    top_context_score=0.0,
                    plugins_executed=[],
                    confidence_score=0.0
                )
                return ChatResponse(
                    response="I apologize, but I encountered an error while processing your request. Please try again.",
                    session_id=session_id,
                    config=config,
                    metrics=error_metrics
                )

    async def _retrieve_context(self, message: str, config: ChatConfig, user_id: Optional[str], context: ConversationContext, **kwargs) -> AggregatedContext:
        aggregation_config = AggregationConfig(
            strategy=config.aggregation_strategy,
            max_results=config.max_context_results
        )
        return await self.context_aggregator.aggregate_context(
            query=message, config=aggregation_config, user_id=user_id, **kwargs
        )

    async def _process_plugins(self, message: str, aggregated_context: AggregatedContext, config: ChatConfig, context: ConversationContext) -> Dict[str, Any]:
        if not config.enable_plugins or not self.plugin_manager:
            return {}
        return await self.plugin_manager.process_message(message, aggregated_context, context.metadata)

    async def _coordinate_llm_session(self, session_id: str, user_id: str, is_first_request: bool):
        """Coordinate session state with the LLM client if it supports session management."""
        try:
            llm_client = get_llm_client()
            
            # Check if the LLM client supports session management (like VertexADKClient)
            if hasattr(llm_client, 'get_current_session_id'):
                current_session = llm_client.get_current_session_id()
                logger.debug(f"LLM client current session: {current_session}")
                
                # If this is a first request but LLM client has a different session,
                # we might want to reset or create a new session
                if is_first_request and current_session:
                    logger.info(f"First request detected but LLM client has session {current_session}, resetting")
                    if hasattr(llm_client, 'reset_session'):
                        await llm_client.reset_session()
                
            # Additional coordination logic can be added here for other session-aware clients
            
        except Exception as e:
            logger.warning(f"Error coordinating LLM session: {e}")
            # Don't fail the request due to session coordination issues

    async def _generate_response(self, message: str, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any], config: ChatConfig, context: ConversationContext, db: async_session, is_first_request: bool = False) -> str:
        prompt = await self._build_prompt(message, aggregated_context, plugin_results, config, context, db, is_first_request)
        
        if config.use_local_llm and self.ollama_service:
            return await self.ollama_service.generate_text(prompt, max_tokens=config.max_tokens, temperature=config.temperature)
        else:
            llm_client = get_llm_client()
            return await llm_client.generate(prompt)

    async def _build_prompt(self, message: str, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any], config: ChatConfig, context: ConversationContext, db: async_session, is_first_request: bool = False) -> str:
        prompt_builder = get_intelligent_prompt_builder()
        
        recent_transcripts = await self._get_recent_transcripts(context.user_id, db)

        return prompt_builder.build_intelligent_prompt(
            user_message=message,
            aggregated_context=aggregated_context,
            plugin_results=plugin_results,
            config=config,
            conversation_context=context,
            recent_transcripts=recent_transcripts,
            is_first_request=is_first_request
        )

    async def _get_recent_transcripts(self, user_id: str, db: async_session) -> List[str]:
        audio_repo = AudioRepository(db)
        since = datetime.utcnow() - timedelta(hours=settings.recent_transcript_window_hours)
        recent_audio_files = await audio_repo.list_with_filters(
            user_id=user_id,
            status="completed",
            limit=10, # Limit to 10 most recent
            offset=0,
            from_date=since
        )
        audio_files, _ = recent_audio_files
        return [f.improved_transcript for f in audio_files if f.improved_transcript]

    async def _save_and_process_conversation(self, repo: ConversationHistoryRepository, session_id: str, user_id: str, user_message: str, assistant_response: str, context: AggregatedContext):
        history_entry = await repo.create({
            "session_id": session_id,
            "user_id": user_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "extra_data": {"context_summary": context.get_summary_stats()}
        })

        from workers.tasks.conversation_processing_tasks import process_conversation_history
        process_conversation_history.apply_async(
            args=[str(history_entry.id)],
            countdown=settings.conversation_processing_delay_minutes * 60
        )

    def _extract_sources(self, aggregated_context: AggregatedContext, config: ChatConfig) -> List[Dict[str, Any]]:
        if not config.include_sources or not aggregated_context.results:
            return []
        return [r.to_dict() for r in aggregated_context.results[:5]]

    def _generate_suggestions(self, message: str, aggregated_context: AggregatedContext, config: ChatConfig) -> List[str]:
        return ["Tell me more about that."]
    
    def _calculate_confidence(self, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any]) -> float:
        """Calculate confidence score based on context quality and plugin results."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on context quality
        if aggregated_context and aggregated_context.results:
            top_scores = [r.unified_score for r in aggregated_context.results[:3]]
            if top_scores:
                avg_top_score = sum(top_scores) / len(top_scores)
                confidence = 0.3 + (avg_top_score * 0.5)  # 30-80% based on context
        
        # Boost confidence if plugins provided additional data
        if plugin_results and plugin_results.get("results"):
            confidence = min(confidence + 0.1, 0.95)  # Add 10% for plugin data, cap at 95%
        
        return round(confidence, 2)