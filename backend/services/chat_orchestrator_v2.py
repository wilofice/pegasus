"""Modern Chat Orchestrator V2 integrating context aggregation, ranking, and LLM services."""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from services.context_aggregator_v2 import ContextAggregatorV2, AggregatedContext, AggregationConfig, AggregationStrategy
from services.context_ranker import RankingStrategy
from services.llm_client import get_llm_client
from services.intelligent_prompt_builder import get_intelligent_prompt_builder
from services.ollama_service import OllamaService
from services.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


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
    context_used: Optional[AggregatedContext] = None
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


class ChatOrchestratorV2:
    """Modern chat orchestrator with context aggregation, ranking, and plugin integration."""
    
    def __init__(self,
                 context_aggregator: ContextAggregatorV2,
                 plugin_manager: Optional[PluginManager] = None,
                 ollama_service: Optional[OllamaService] = None,
                 default_config: Optional[ChatConfig] = None):
        """Initialize chat orchestrator.
        
        Args:
            context_aggregator: Context aggregation service
            plugin_manager: Plugin management service
            ollama_service: Local LLM service
            default_config: Default chat configuration
        """
        self.context_aggregator = context_aggregator
        self.plugin_manager = plugin_manager
        self.ollama_service = ollama_service
        self.default_config = default_config or ChatConfig()
        
        # Session management
        self.sessions: Dict[str, ConversationContext] = {}
        
        logger.info("Chat Orchestrator V2 initialized with modern services")
    
    async def chat(self,
                   message: str,
                   session_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   config: Optional[ChatConfig] = None,
                   conversation_context: Optional[ConversationContext] = None,
                   **kwargs) -> ChatResponse:
        """Process a chat message and generate response.
        
        Args:
            message: User message
            session_id: Session identifier
            user_id: User identifier
            config: Chat configuration
            conversation_context: Existing conversation context
            **kwargs: Additional parameters
            
        Returns:
            Complete chat response with metadata
        """
        start_time = datetime.now()
        config = config or self.default_config
        session_id = session_id or str(uuid.uuid4())
        
        try:
            logger.info(f"Processing chat message for session {session_id}: '{message[:50]}...'")
            
            # Initialize metrics
            metrics = ChatMetrics(
                context_retrieval_time_ms=0,
                llm_generation_time_ms=0,
                plugin_processing_time_ms=0,
                total_processing_time_ms=0,
                context_results_count=0,
                top_context_score=0.0,
                plugins_executed=[]
            )
            
            # Get or create conversation context
            if conversation_context:
                context = conversation_context
            else:
                context = self._get_or_create_session(session_id, user_id)
            
            # Step 1: Context Retrieval
            context_start = datetime.now()
            aggregated_context = await self._retrieve_context(
                message, config, user_id, context, **kwargs
            )
            context_time = (datetime.now() - context_start).total_seconds() * 1000
            metrics.context_retrieval_time_ms = context_time
            metrics.context_results_count = len(aggregated_context.results)
            
            if aggregated_context.results:
                metrics.top_context_score = aggregated_context.results[0].unified_score
            
            # Step 2: Plugin Processing
            plugin_start = datetime.now()
            plugin_results = await self._process_plugins(
                message, aggregated_context, config, context
            )
            plugin_time = (datetime.now() - plugin_start).total_seconds() * 1000
            metrics.plugin_processing_time_ms = plugin_time
            metrics.plugins_executed = plugin_results.get("executed_plugins", [])
            
            # Step 3: LLM Generation
            llm_start = datetime.now()
            response_text = await self._generate_response(
                message, aggregated_context, plugin_results, config, context
            )
            llm_time = (datetime.now() - llm_start).total_seconds() * 1000
            metrics.llm_generation_time_ms = llm_time
            
            # Step 4: Post-processing
            sources = self._extract_sources(aggregated_context, config)
            suggestions = self._generate_suggestions(message, aggregated_context, config)
            confidence = self._calculate_confidence(aggregated_context, plugin_results)
            metrics.confidence_score = confidence
            
            # Update conversation context
            self._update_conversation_context(context, message, response_text)
            
            # Calculate total time
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            metrics.total_processing_time_ms = total_time
            
            # Create response
            chat_response = ChatResponse(
                response=response_text,
                session_id=session_id,
                config=config,
                metrics=metrics,
                context_used=aggregated_context,
                sources=sources,
                suggestions=suggestions,
                metadata={
                    "user_id": user_id,
                    "timestamp": start_time.isoformat(),
                    "conversation_turns": len(context.conversation_history)
                }
            )
            
            logger.info(f"Chat response generated in {total_time:.1f}ms with {len(sources)} sources")
            return chat_response
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            
            # Return error response
            error_metrics = ChatMetrics(
                context_retrieval_time_ms=0,
                llm_generation_time_ms=0,
                plugin_processing_time_ms=0,
                total_processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                context_results_count=0,
                top_context_score=0.0,
                plugins_executed=[]
            )
            
            return ChatResponse(
                response="I apologize, but I encountered an error processing your request. Please try again.",
                session_id=session_id,
                config=config,
                metrics=error_metrics,
                metadata={"error": str(e), "timestamp": start_time.isoformat()}
            )
    
    async def _retrieve_context(self,
                               message: str,
                               config: ChatConfig,
                               user_id: Optional[str],
                               conversation_context: ConversationContext,
                               **kwargs) -> AggregatedContext:
        """Retrieve relevant context for the message."""
        try:
            # Configure aggregation based on conversation mode
            aggregation_config = self._create_aggregation_config(config, conversation_context)
            
            # Retrieve context
            aggregated_context = await self.context_aggregator.aggregate_context(
                query=message,
                config=aggregation_config,
                user_id=user_id,
                **kwargs
            )
            
            logger.debug(f"Retrieved {len(aggregated_context.results)} context results")
            return aggregated_context
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            # Return empty context
            from services.context_aggregator_v2 import AggregatedContext, AggregationMetrics
            return AggregatedContext(
                results=[],
                query=message,
                config=AggregationConfig(),
                metrics=AggregationMetrics(
                    total_retrieval_time_ms=0,
                    total_ranking_time_ms=0,
                    total_processing_time_ms=0,
                    vector_results_count=0,
                    graph_results_count=0,
                    final_results_count=0,
                    duplicates_removed=0,
                    strategy_used="error",
                    ranking_strategy_used="error"
                )
            )
    
    async def _process_plugins(self,
                              message: str,
                              aggregated_context: AggregatedContext,
                              config: ChatConfig,
                              conversation_context: ConversationContext) -> Dict[str, Any]:
        """Process message through available plugins."""
        try:
            if not config.enable_plugins or not self.plugin_manager:
                return {"executed_plugins": [], "results": {}}
            
            # Run plugins with timeout
            plugin_results = await asyncio.wait_for(
                self.plugin_manager.process_message(
                    message=message,
                    context=aggregated_context,
                    conversation_context=conversation_context.metadata
                ),
                timeout=config.plugin_timeout
            )
            
            logger.debug(f"Processed through {len(plugin_results.get('executed_plugins', []))} plugins")
            return plugin_results
            
        except asyncio.TimeoutError:
            logger.warning("Plugin processing timed out")
            return {"executed_plugins": [], "results": {}, "timeout": True}
        except Exception as e:
            logger.error(f"Plugin processing failed: {e}")
            return {"executed_plugins": [], "results": {}, "error": str(e)}
    
    async def _generate_response(self,
                                message: str,
                                aggregated_context: AggregatedContext,
                                plugin_results: Dict[str, Any],
                                config: ChatConfig,
                                conversation_context: ConversationContext) -> str:
        """Generate LLM response with context and plugins."""
        try:
            # Build prompt with context and conversation history
            prompt = self._build_prompt(
                message, aggregated_context, plugin_results, config, conversation_context
            )
            
            # Generate response
            if config.use_local_llm and self.ollama_service:
                response = await self._generate_local_response(prompt, config)
            else:
                response = await self._generate_external_response(prompt, config)
            
            # Apply response style formatting
            response = self._format_response(response, config)
            
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "I apologize, but I'm unable to generate a response at the moment. Please try again."
    
    def _build_prompt(self,
                     message: str,
                     aggregated_context: AggregatedContext,
                     plugin_results: Dict[str, Any],
                     config: ChatConfig,
                     conversation_context: ConversationContext) -> str:
        """Build comprehensive prompt for LLM using intelligent prompt builder."""
        try:
            # Use intelligent prompt builder for sophisticated prompting
            prompt_builder = get_intelligent_prompt_builder()
            
            intelligent_prompt = prompt_builder.build_intelligent_prompt(
                user_message=message,
                aggregated_context=aggregated_context,
                plugin_results=plugin_results,
                config=config,
                conversation_context=conversation_context
            )
            
            logger.info("Generated intelligent prompt for LLM")
            return intelligent_prompt
            
        except Exception as e:
            logger.error(f"Intelligent prompt building failed, using fallback: {e}")
            # Fallback to original simple prompt
            return self._build_simple_prompt(message, aggregated_context, plugin_results, config, conversation_context)
    
    def _build_simple_prompt(self,
                            message: str,
                            aggregated_context: AggregatedContext,
                            plugin_results: Dict[str, Any],
                            config: ChatConfig,
                            conversation_context: ConversationContext) -> str:
        """Build simple prompt as fallback (original implementation)."""
        try:
            prompt_parts = []
            
            # System prompt based on conversation mode
            system_prompt = self._get_system_prompt(config.conversation_mode, config.response_style)
            prompt_parts.append(system_prompt)
            
            # Context information
            if aggregated_context.results:
                context_text = self._format_context_for_prompt(aggregated_context, config)
                prompt_parts.append(f"Relevant Context:\n{context_text}")
            
            # Plugin results
            if plugin_results.get("results"):
                plugin_text = self._format_plugin_results_for_prompt(plugin_results)
                prompt_parts.append(f"Additional Information:\n{plugin_text}")
            
            # Conversation history
            if conversation_context.conversation_history:
                history_text = self._format_conversation_history(conversation_context)
                prompt_parts.append(f"Conversation History:\n{history_text}")
            
            # Current user message
            prompt_parts.append(f"User Question: {message}")
            
            # Response guidelines
            guidelines = self._get_response_guidelines(config)
            prompt_parts.append(guidelines)
            
            return "\n\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Simple prompt building failed: {e}")
            return f"Please respond to: {message}"
    
    async def _generate_local_response(self, prompt: str, config: ChatConfig) -> str:
        """Generate response using local Ollama service."""
        try:
            if not self.ollama_service:
                raise ValueError("Ollama service not available")
            
            # Use Ollama for generation
            response = await self.ollama_service.generate_text(
                prompt=prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}")
            raise
    
    async def _generate_external_response(self, prompt: str, config: ChatConfig) -> str:
        """Generate response using external LLM service."""
        try:
            # Use external LLM client
            llm_client = get_llm_client()
            response = await llm_client.generate(prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"External LLM generation failed: {e}")
            raise
    
    def _format_response(self, response: str, config: ChatConfig) -> str:
        """Format response according to style preferences."""
        try:
            if config.response_style == ResponseStyle.CONCISE:
                # Keep response brief
                sentences = response.split('. ')
                if len(sentences) > 3:
                    response = '. '.join(sentences[:3]) + '.'
            
            elif config.response_style == ResponseStyle.ACADEMIC:
                # Add more formal structure
                if not response.startswith("Based on"):
                    response = f"Based on the available information, {response.lower()}"
            
            elif config.response_style == ResponseStyle.CASUAL:
                # Make more conversational
                response = response.replace("Based on the provided context", "Looking at what I know")
                response = response.replace("In conclusion", "So")
            
            return response
            
        except Exception as e:
            logger.warning(f"Response formatting failed: {e}")
            return response
    
    def _extract_sources(self, aggregated_context: AggregatedContext, config: ChatConfig) -> List[Dict[str, Any]]:
        """Extract source information from context."""
        try:
            if not config.include_sources or not aggregated_context.results:
                return []
            
            sources = []
            for i, result in enumerate(aggregated_context.results[:5]):  # Top 5 sources
                source = {
                    "id": result.id,
                    "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "score": result.unified_score,
                    "source_type": result.source_type,
                    "rank": i + 1
                }
                
                # Add metadata if available
                if result.metadata:
                    source.update({
                        "audio_id": result.metadata.get("audio_id"),
                        "timestamp": result.metadata.get("created_at"),
                        "entities": result.metadata.get("entities", [])
                    })
                
                sources.append(source)
            
            return sources
            
        except Exception as e:
            logger.warning(f"Source extraction failed: {e}")
            return []
    
    def _generate_suggestions(self, message: str, aggregated_context: AggregatedContext, config: ChatConfig) -> List[str]:
        """Generate follow-up suggestions based on context."""
        try:
            suggestions = []
            
            if aggregated_context.results:
                # Extract entities and topics for suggestions
                entities = set()
                for result in aggregated_context.results[:3]:
                    if result.entities:
                        entities.update([e.get("text", e) if isinstance(e, dict) else str(e) 
                                       for e in result.entities])
                
                # Generate entity-based suggestions
                for entity in list(entities)[:2]:
                    suggestions.append(f"Tell me more about {entity}")
                
                # Add related topic suggestions
                if "analysis" not in message.lower():
                    suggestions.append("Can you analyze this further?")
                
                if "example" not in message.lower():
                    suggestions.append("Can you provide examples?")
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            logger.warning(f"Suggestion generation failed: {e}")
            return []
    
    def _calculate_confidence(self, aggregated_context: AggregatedContext, plugin_results: Dict[str, Any]) -> float:
        """Calculate confidence score for the response."""
        try:
            if not aggregated_context.results:
                return 0.1
            
            # Base confidence from top result score
            top_score = aggregated_context.results[0].unified_score
            confidence = top_score
            
            # Boost confidence if multiple high-scoring results
            high_score_count = len([r for r in aggregated_context.results if r.unified_score > 0.7])
            if high_score_count > 1:
                confidence = min(1.0, confidence + 0.1)
            
            # Boost confidence if plugins provided additional info
            if plugin_results.get("results"):
                confidence = min(1.0, confidence + 0.05)
            
            return round(confidence, 3)
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")
            return 0.5
    
    def _get_or_create_session(self, session_id: str, user_id: Optional[str]) -> ConversationContext:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
        
        return self.sessions[session_id]
    
    def _update_conversation_context(self, context: ConversationContext, message: str, response: str):
        """Update conversation context with new exchange."""
        context.conversation_history.append({
            "user": message,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 exchanges
        if len(context.conversation_history) > 10:
            context.conversation_history = context.conversation_history[-10:]
        
        context.last_updated = datetime.now()
        self.sessions[context.session_id] = context
    
    def _create_aggregation_config(self, config: ChatConfig, conversation_context: ConversationContext) -> AggregationConfig:
        """Create aggregation config based on chat config."""
        from services.context_aggregator_v2 import AggregationConfig
        
        return AggregationConfig(
            strategy=config.aggregation_strategy,
            max_results=config.max_context_results,
            ranking_strategy=config.ranking_strategy,
            include_related=True,
            timeout_seconds=config.context_timeout
        )
    
    def _get_system_prompt(self, mode: ConversationMode, style: ResponseStyle) -> str:
        """Get system prompt based on conversation mode and style."""
        base_prompt = "You are a helpful AI assistant with access to relevant context information."
        
        mode_prompts = {
            ConversationMode.RESEARCH: "Focus on providing comprehensive, well-researched responses with citations when possible.",
            ConversationMode.CREATIVE: "Be creative and imaginative in your responses while staying grounded in the provided context.",
            ConversationMode.ANALYTICAL: "Provide analytical, logical responses that break down complex topics systematically.",
            ConversationMode.CONVERSATIONAL: "Be conversational and engaging while providing helpful information."
        }
        
        style_prompts = {
            ResponseStyle.CONCISE: "Keep responses brief and to the point.",
            ResponseStyle.DETAILED: "Provide comprehensive, detailed explanations.",
            ResponseStyle.ACADEMIC: "Use formal, academic language and structure.",
            ResponseStyle.CASUAL: "Use casual, friendly language.",
            ResponseStyle.PROFESSIONAL: "Maintain a professional but approachable tone."
        }
        
        return f"{base_prompt} {mode_prompts.get(mode, '')} {style_prompts.get(style, '')}"
    
    def _format_context_for_prompt(self, aggregated_context: AggregatedContext, config: ChatConfig) -> str:
        """Format context results for inclusion in prompt."""
        try:
            context_parts = []
            for i, result in enumerate(aggregated_context.results[:5]):  # Top 5 results
                context_parts.append(f"[Source {i+1}] {result.content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.warning(f"Context formatting failed: {e}")
            return "No context available."
    
    def _format_plugin_results_for_prompt(self, plugin_results: Dict[str, Any]) -> str:
        """Format plugin results for inclusion in prompt."""
        try:
            if not plugin_results.get("results"):
                return ""
            
            parts = []
            for plugin_name, result in plugin_results["results"].items():
                if isinstance(result, dict) and result.get("output"):
                    parts.append(f"{plugin_name}: {result['output']}")
            
            return "\n".join(parts)
            
        except Exception as e:
            logger.warning(f"Plugin result formatting failed: {e}")
            return ""
    
    def _format_conversation_history(self, conversation_context: ConversationContext) -> str:
        """Format conversation history for prompt."""
        try:
            if not conversation_context.conversation_history:
                return ""
            
            # Include last 3 exchanges
            recent_history = conversation_context.conversation_history[-3:]
            history_parts = []
            
            for exchange in recent_history:
                history_parts.append(f"User: {exchange['user']}")
                history_parts.append(f"Assistant: {exchange['assistant']}")
            
            return "\n".join(history_parts)
            
        except Exception as e:
            logger.warning(f"History formatting failed: {e}")
            return ""
    
    def _get_response_guidelines(self, config: ChatConfig) -> str:
        """Get response guidelines based on configuration."""
        guidelines = ["Please provide a helpful, accurate response based on the context provided."]
        
        if config.include_sources:
            guidelines.append("Reference specific sources when possible.")
        
        if config.conversation_mode == ConversationMode.RESEARCH:
            guidelines.append("Cite sources and provide evidence for claims.")
        
        return " ".join(guidelines)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of chat orchestrator and dependencies."""
        try:
            health = {
                "service": "ChatOrchestratorV2",
                "status": "healthy",
                "dependencies": {},
                "sessions": {
                    "active_sessions": len(self.sessions),
                    "total_conversations": sum(len(s.conversation_history) for s in self.sessions.values())
                }
            }
            
            # Check context aggregator
            try:
                aggregator_health = await self.context_aggregator.health_check()
                health["dependencies"]["context_aggregator"] = aggregator_health
            except Exception as e:
                health["dependencies"]["context_aggregator"] = {"status": "unhealthy", "error": str(e)}
            
            # Check plugin manager
            if self.plugin_manager:
                try:
                    plugin_health = await self.plugin_manager.health_check()
                    health["dependencies"]["plugin_manager"] = plugin_health
                except Exception as e:
                    health["dependencies"]["plugin_manager"] = {"status": "unhealthy", "error": str(e)}
            
            # Check Ollama service
            if self.ollama_service:
                try:
                    ollama_health = await self.ollama_service.health_check()
                    health["dependencies"]["ollama_service"] = ollama_health
                except Exception as e:
                    health["dependencies"]["ollama_service"] = {"status": "unhealthy", "error": str(e)}
            
            # Overall health
            unhealthy_deps = [k for k, v in health["dependencies"].items() 
                            if v.get("status") != "healthy"]
            
            if unhealthy_deps:
                health["status"] = "degraded"
                health["unhealthy_dependencies"] = unhealthy_deps
            
            return health
            
        except Exception as e:
            return {
                "service": "ChatOrchestratorV2",
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session."""
        if session_id not in self.sessions:
            return None
        
        context = self.sessions[session_id]
        return {
            "session_id": session_id,
            "user_id": context.user_id,
            "created_at": context.created_at.isoformat(),
            "last_updated": context.last_updated.isoformat(),
            "conversation_turns": len(context.conversation_history),
            "metadata": context.metadata
        }
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def clear_all_sessions(self) -> int:
        """Clear all conversation sessions."""
        count = len(self.sessions)
        self.sessions.clear()
        return count