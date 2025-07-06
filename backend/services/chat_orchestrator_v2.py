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
        
        async with async_session() as db:
            try:
                history_repo = ConversationHistoryRepository(db)
                
                metrics = ChatMetrics(total_processing_time_ms=0)
                
                conversation_history = await history_repo.get_recent_for_user(
                    user_id, settings.conversation_history_lookback_days
                )
                
                context = ConversationContext(
                    session_id=session_id,
                    user_id=user_id,
                    conversation_history=[h.to_dict() for h in conversation_history]
                )

                aggregated_context = await self._retrieve_context(message, config, user_id, context, **kwargs)
                
                plugin_results = await self._process_plugins(message, aggregated_context, config, context)
                
                response_text = await self._generate_response(
                    message, aggregated_context, plugin_results, config, context, db
                )
                
                await self._save_and_process_conversation(
                    history_repo, session_id, user_id, message, response_text, aggregated_context
                )

                total_time = (datetime.now() - start_time).total_seconds() * 1000
                metrics.total_processing_time_ms = total_time

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
                return ChatResponse(response="An error occurred.", session_id=session_id, config=config)

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

    async def _generate_response(self, message: str, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any], config: ChatConfig, context: ConversationContext, db: async_session) -> str:
        prompt = await self._build_prompt(message, aggregated_context, plugin_results, config, context, db)
        
        if config.use_local_llm and self.ollama_service:
            return await self.ollama_service.generate_text(prompt, max_tokens=config.max_tokens, temperature=config.temperature)
        else:
            llm_client = get_llm_client()
            return await llm_client.generate(prompt)

    async def _build_prompt(self, message: str, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any], config: ChatConfig, context: ConversationContext, db: async_session) -> str:
        prompt_builder = get_intelligent_prompt_builder()
        
        recent_transcripts = await self._get_recent_transcripts(context.user_id, db)

        return prompt_builder.build_intelligent_prompt(
            user_message=message,
            aggregated_context=aggregated_context,
            plugin_results=plugin_results,
            config=config,
            conversation_context=context,
            recent_transcripts=recent_transcripts
        )

    async def _get_recent_transcripts(self, user_id: str, db: async_session) -> List[str]:
        audio_repo = AudioRepository(db)
        since = datetime.utcnow() - timedelta(hours=settings.recent_transcript_window_hours)
        recent_audio_files = await audio_repo.list_with_filters(
            user_id=user_id,
            status="completed",
            limit=10, # Limit to 10 most recent
            offset=0,
            created_after=since
        )
        return [f.improved_transcript for f, _ in recent_audio_files]

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