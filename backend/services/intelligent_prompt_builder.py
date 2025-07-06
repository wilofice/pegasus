"""
Intelligent Prompt Builder for LLM Chat Generation

This module creates sophisticated, context-aware prompts that help the LLM
provide accurate, relevant, and well-informed responses using all available context.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from services.context_aggregator_v2 import AggregatedContext
from services.chat_types import ChatConfig, ConversationMode, ResponseStyle, ConversationContext

logger = logging.getLogger(__name__)


class PromptTemplate(Enum):
    """Available prompt templates for different scenarios."""
    COMPREHENSIVE = "comprehensive"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"


class IntelligentPromptBuilder:
    """
    Advanced prompt builder that creates context-aware, intelligent prompts
    for LLM generation with optimal information utilization.
    """
    
    def __init__(self):
        self.templates = self._load_prompt_templates()
    
    def build_intelligent_prompt(self,
                                user_message: str,
                                aggregated_context: AggregatedContext,
                                plugin_results: Dict[str, Any],
                                config: ChatConfig,
                                conversation_context: ConversationContext,
                                recent_transcripts: List[str]) -> str:
        """
        Build an intelligent, comprehensive prompt that maximizes context utilization.
        """
        try:
            logger.debug(f"Starting intelligent prompt building for message: {user_message[:50]}...")
            
            # Determine prompt strategy with error handling
            try:
                prompt_strategy = self._determine_prompt_strategy(user_message, aggregated_context, config)
                logger.debug(f"Determined prompt strategy: {prompt_strategy}")
            except Exception as e:
                logger.error(f"Error determining prompt strategy: {e}", exc_info=True)
                prompt_strategy = "conversational_balanced"  # Safe fallback
            
            prompt_components = []
            
            # Build system instructions with error handling
            try:
                system_prompt = self._build_system_instructions(config, prompt_strategy)
                prompt_components.append(system_prompt)
                logger.debug("Added system instructions")
            except Exception as e:
                logger.error(f"Error building system instructions: {e}", exc_info=True)
                prompt_components.append("You are a helpful AI assistant.")

            # Build transcript section with error handling
            if recent_transcripts:
                try:
                    transcript_section = self._build_transcript_section(recent_transcripts)
                    prompt_components.append(transcript_section)
                    logger.debug(f"Added transcript section with {len(recent_transcripts)} transcripts")
                except Exception as e:
                    logger.error(f"Error building transcript section: {e}", exc_info=True)
            
            # Build context section with error handling
            if aggregated_context and hasattr(aggregated_context, 'results') and aggregated_context.results:
                try:
                    context_section = self._build_context_section(aggregated_context, config)
                    prompt_components.append(context_section)
                    logger.debug(f"Added context section with {len(aggregated_context.results)} results")
                except Exception as e:
                    logger.error(f"Error building context section: {e}", exc_info=True)
            
            # Build plugin section with error handling
            if plugin_results and plugin_results.get("results"):
                try:
                    plugin_section = self._build_plugin_section(plugin_results)
                    if plugin_section.strip():  # Only add if not empty
                        prompt_components.append(plugin_section)
                        logger.debug("Added plugin section")
                except Exception as e:
                    logger.error(f"Error building plugin section: {e}", exc_info=True)
            
            # Build conversation section with error handling
            if conversation_context and hasattr(conversation_context, 'conversation_history') and conversation_context.conversation_history:
                try:
                    history_section = self._build_conversation_section(conversation_context)
                    if history_section.strip():  # Only add if not empty
                        prompt_components.append(history_section)
                        logger.debug(f"Added conversation section with {len(conversation_context.conversation_history)} exchanges")
                except Exception as e:
                    logger.error(f"Error building conversation section: {e}", exc_info=True)
            
            # Build task instructions with error handling
            try:
                task_instructions = self._build_task_instructions(user_message, aggregated_context, config)
                prompt_components.append(task_instructions)
                logger.debug("Added task instructions")
            except Exception as e:
                logger.error(f"Error building task instructions: {e}", exc_info=True)
                prompt_components.append(f"=== CURRENT TASK ===\nUser Question: {user_message}")
            
            # Build response framework with error handling
            try:
                response_framework = self._build_response_framework(config, aggregated_context)
                prompt_components.append(response_framework)
                logger.debug("Added response framework")
            except Exception as e:
                logger.error(f"Error building response framework: {e}", exc_info=True)
            
            # Build quality instructions with error handling
            try:
                quality_instructions = self._build_quality_instructions(config)
                prompt_components.append(quality_instructions)
                logger.debug("Added quality instructions")
            except Exception as e:
                logger.error(f"Error building quality instructions: {e}", exc_info=True)
            
            # Join all components, filtering out empty ones
            valid_components = [comp for comp in prompt_components if comp and comp.strip()]
            full_prompt = "\n\n".join(valid_components)
            
            logger.info(f"Built intelligent prompt with {len(valid_components)} sections, total length: {len(full_prompt)}")
            return full_prompt
            
        except Exception as e:
            logger.error(f"Critical error in intelligent prompt building: {e}", exc_info=True)
            return self._build_fallback_prompt(user_message, aggregated_context, config)
    
    def _determine_prompt_strategy(self,
                                  user_message: str,
                                  aggregated_context: AggregatedContext,
                                  config: ChatConfig) -> str:
        """Analyze the request and context to determine optimal prompt strategy."""
        # Analyze user message characteristics
        is_factual_query = any(word in user_message.lower() for word in 
                              ['what', 'when', 'where', 'who', 'how', 'why', 'define', 'explain'])
        is_analytical_query = any(word in user_message.lower() for word in 
                                 ['analyze', 'compare', 'evaluate', 'assess', 'examine'])
        is_creative_query = any(word in user_message.lower() for word in 
                               ['create', 'generate', 'design', 'imagine', 'brainstorm'])
        
        # Consider available context
        has_rich_context = aggregated_context.results and len(aggregated_context.results) > 2
        
        # Determine strategy
        if config.conversation_mode == ConversationMode.RESEARCH or (is_factual_query and has_rich_context):
            return "research_intensive"
        elif config.conversation_mode == ConversationMode.ANALYTICAL or is_analytical_query:
            return "analytical_deep"
        elif config.conversation_mode == ConversationMode.CREATIVE or is_creative_query:
            return "creative_synthesis"
        else:
            return "conversational_balanced"
    
    def _build_system_instructions(self, config: ChatConfig, strategy: str) -> str:
        """Build comprehensive system instructions based on strategy."""
        base_instructions = """You are Pegasus Brain, an advanced AI assistant acting as a life coach and personal adviser. You have access to comprehensive contextual information from various sources including audio transcriptions, documents, and real-time analysis.

PEGASUS BRAIN ROLE & IDENTITY:
As a life coach and personal adviser, your mission is to:
- Guide your client user toward personal growth, self-awareness, and goal achievement
- Provide thoughtful, empathetic support for life challenges and decisions
- Help the user identify patterns, insights, and opportunities from their experiences
- Offer constructive feedback and actionable advice based on their personal context
- Maintain a supportive, non-judgmental, and encouraging approach
- Foster accountability and motivation while respecting user autonomy
- Help user connect their experiences to meaningful life improvements

COACHING APPROACH:
- Ask insightful questions to help users reflect and gain clarity
- Provide personalized guidance based on their unique circumstances
- Encourage self-discovery and empowerment rather than prescriptive solutions
- Help user identify their values, strengths, and areas for growth
- Support goal-setting and progress tracking through their shared experiences
- Recognize emotional patterns and provide appropriate support

CRITICAL ANTI-HALLUCINATION RULES:
1. You MUST ONLY use information explicitly provided in the context, conversation history, or recent transcripts
2. You MUST NOT make up, invent, or hallucinate any facts, details, or information
3. If information is not available in the provided context, you MUST say so explicitly
4. You MUST NOT use external knowledge beyond what is provided in the context
5. Every claim you make MUST be directly traceable to the provided information

Your core capabilities:
- Deep contextual understanding from multiple information sources
- Accurate information synthesis and analysis ONLY from provided context
- Intelligent reasoning and inference BASED ON available data
- Source-aware response generation WITH strict adherence to sources
- Conversation continuity and memory FROM provided history only
- Life coaching expertise applied to user's personal context and experiences"""

        strategy_instructions = {
            "research_intensive": """
Focus on:
• Thorough analysis of all provided context
• Evidence-based reasoning and conclusions
• Comprehensive information synthesis
• Accurate citation and source reference
• Detailed, well-researched responses""",
            
            "analytical_deep": """
Focus on:
• Systematic breakdown of complex information
• Logical reasoning and structured analysis
• Pattern identification across sources
• Critical evaluation of information
• Clear, methodical explanations""",
            
            "creative_synthesis": """
Focus on:
• Creative integration of available information
• Innovative connections between concepts
• Imaginative but grounded responses
• Context-aware creative solutions
• Balanced creativity with factual accuracy""",
            
            "conversational_balanced": """
Focus on:
• Natural, engaging conversation flow
• Balanced use of available context
• Clear, accessible explanations
• Relevant and helpful responses
• Adaptive tone and style"""
        }
        
        style_modifier = {
            ResponseStyle.CONCISE: "\\nCommunication Style: Be concise and direct while maintaining completeness.",
            ResponseStyle.DETAILED: "\\nCommunication Style: Provide comprehensive, detailed explanations with full context.",
            ResponseStyle.ACADEMIC: "\\nCommunication Style: Use formal, academic language with proper structure and citations.",
            ResponseStyle.CASUAL: "\\nCommunication Style: Use friendly, casual language while maintaining accuracy.",
            ResponseStyle.PROFESSIONAL: "\\nCommunication Style: Maintain professional tone with clear, business-appropriate language."
        }
        
        return (base_instructions + 
                strategy_instructions.get(strategy, strategy_instructions["conversational_balanced"]) +
                style_modifier.get(config.response_style, ""))
    
    def _build_context_section(self, aggregated_context: AggregatedContext, config: ChatConfig) -> str:
        """Build intelligent context section with source analysis."""
        context_header = "=== CONTEXTUAL INFORMATION ==="
        
        context_parts = []
        
        # Group context by source type for better organization
        vector_results = [r for r in aggregated_context.results if r.source_type == "vector"]
        graph_results = [r for r in aggregated_context.results if r.source_type == "graph"]
        hybrid_results = [r for r in aggregated_context.results if r.source_type not in ["vector", "graph"]]
        
        # Vector context (semantic similarity)
        if vector_results:
            context_parts.append("SEMANTIC CONTEXT (Similar Content):")
            for i, result in enumerate(vector_results[:3], 1):
                confidence_indicator = self._get_confidence_indicator(result.unified_score)
                context_parts.append(f"[Source {i}] {confidence_indicator} {result.content}")
                if hasattr(result, 'metadata') and result.metadata:
                    context_parts.append(f"  Context: {self._format_metadata(result.metadata)}")
        
        # Graph context (connected information)
        if graph_results:
            context_parts.append("\\nCONNECTED KNOWLEDGE (Related Information):")
            for i, result in enumerate(graph_results[:3], 1):
                confidence_indicator = self._get_confidence_indicator(result.unified_score)
                context_parts.append(f"[Graph {i}] {confidence_indicator} {result.content}")
        
        # Hybrid/other context
        if hybrid_results:
            context_parts.append("\\nADDITIONAL CONTEXT:")
            for i, result in enumerate(hybrid_results[:2], 1):
                confidence_indicator = self._get_confidence_indicator(result.unified_score)
                context_parts.append(f"[Additional {i}] {confidence_indicator} {result.content}")
        
        # Context analysis summary
        total_sources = len(aggregated_context.results)
        context_parts.append(f"\\nCONTEXT SUMMARY: {total_sources} sources analyzed")
        
        if total_sources > 0:
            avg_confidence = sum(r.unified_score for r in aggregated_context.results) / total_sources
            context_parts.append(f"Average Relevance: {avg_confidence:.2f}")
        
        return context_header + "\\n" + "\\n".join(context_parts)
    
    def _build_plugin_section(self, plugin_results: Dict[str, Any]) -> str:
        """Build plugin results section."""
        plugin_header = "=== ADDITIONAL ANALYSIS ==="
        plugin_parts = []
        
        if plugin_results.get("results"):
            for plugin_name, result in plugin_results["results"].items():
                if isinstance(result, dict) and result.get("output"):
                    plugin_parts.append(f"{plugin_name.upper()}: {result['output']}")
                elif isinstance(result, str):
                    plugin_parts.append(f"{plugin_name.upper()}: {result}")
        
        executed_plugins = plugin_results.get("executed_plugins", [])
        if executed_plugins:
            plugin_parts.append(f"\\nPlugins executed: {', '.join(executed_plugins)}")
        
        return plugin_header + "\\n" + "\\n".join(plugin_parts) if plugin_parts else ""
    
    def _build_conversation_section(self, conversation_context: ConversationContext) -> str:
        """Build conversation history section with comprehensive error handling."""
        try:
            history_header = "=== CONVERSATION CONTEXT ==="
            
            # Validate conversation context
            if not conversation_context:
                logger.warning("Conversation context is None")
                return ""
            
            if not hasattr(conversation_context, 'conversation_history'):
                logger.warning("Conversation context missing conversation_history attribute")
                return ""
            
            recent_history = conversation_context.conversation_history
            if not recent_history:
                logger.debug("No conversation history found")
                return ""
            
            history_parts = []
            valid_exchanges = 0
            
            for i, exchange in enumerate(recent_history, 1):
                try:
                    # Validate exchange data
                    if not isinstance(exchange, dict):
                        logger.warning(f"Exchange {i} is not a dictionary: {type(exchange)}")
                        continue
                    
                    # Handle different possible key formats for conversation history
                    user_message = exchange.get('user_message') or exchange.get('user', '')
                    assistant_message = exchange.get('assistant_response') or exchange.get('assistant', '')
                    
                    # Debug logging for key structure
                    if not user_message and not assistant_message:
                        available_keys = list(exchange.keys())
                        logger.warning(f"Exchange {i} missing expected keys. Available: {available_keys}")
                        continue
                    
                    turn_number = len(recent_history) - len(recent_history) + i
                    history_parts.append(f"Turn {turn_number}:")
                    
                    if user_message:
                        # Sanitize user message
                        clean_user_message = str(user_message).strip()
                        history_parts.append(f"  User: {clean_user_message}")
                    
                    if assistant_message:
                        # Sanitize and truncate assistant message
                        clean_assistant_message = str(assistant_message).strip()
                        truncated_response = clean_assistant_message[:200] + ('...' if len(clean_assistant_message) > 200 else '')
                        history_parts.append(f"  Assistant: {truncated_response}")
                    
                    valid_exchanges += 1
                    
                except Exception as e:
                    logger.error(f"Error processing conversation exchange {i}: {e}", exc_info=True)
                    continue
            
            if valid_exchanges == 0:
                logger.warning("No valid conversation exchanges found")
                return ""
            
            # Build conversation metadata safely
            conversation_meta = []
            try:
                if hasattr(conversation_context, 'user_preferences') and conversation_context.user_preferences:
                    conversation_meta.append(f"User preferences: {conversation_context.user_preferences}")
            except Exception as e:
                logger.error(f"Error accessing user preferences: {e}")
            
            conversation_meta.append(f"Total conversation turns: {len(recent_history)}")
            conversation_meta.append(f"Valid exchanges processed: {valid_exchanges}")
            
            result = (history_header + "\\n" + 
                     "\\n".join(history_parts) + 
                     "\\n\\nConversation Metadata:\\n" + "\\n".join(conversation_meta))
            
            logger.debug(f"Built conversation section with {valid_exchanges} valid exchanges")
            return result
                    
        except Exception as e:
            logger.error(f"Critical error building conversation section: {e}", exc_info=True)
            return ""  # Return empty string on critical error
    
    def _build_task_instructions(self,
                               user_message: str,
                               aggregated_context: AggregatedContext,
                               config: ChatConfig) -> str:
        """Build task-specific instructions."""
        task_header = "=== CURRENT TASK ==="
        
        instructions = [
            f"User Question/Request: {user_message}",
            "",
            "Task Requirements:",
            "• Analyze ALL provided contextual information thoroughly",
            "• Synthesize information from multiple sources when relevant",
            "• Provide accurate, well-reasoned responses based on available context",
            "• Acknowledge limitations when context is insufficient",
            "• Maintain coherence with previous conversation when applicable"
        ]
        
        # Add specific instructions based on context availability
        if aggregated_context.results:
            total_context = len(aggregated_context.results)
            instructions.extend([
                "",
                f"Context Utilization Instructions:",
                f"• You have access to {total_context} relevant sources",
                "• Prioritize information from higher-confidence sources",
                "• Cross-reference information when multiple sources are available",
                "• Identify and resolve any contradictions in the sources"
            ])
        
        return task_header + "\\n" + "\\n".join(instructions)
    
    def _build_response_framework(self, config: ChatConfig, aggregated_context: AggregatedContext) -> str:
        """Build response structure framework."""
        framework_header = "=== RESPONSE FRAMEWORK ==="
        
        framework_parts = [
            "Structure your response as follows:",
            "1. Direct answer to the user's question (if applicable)",
            "2. Supporting information from available context",
            "3. Additional insights or analysis (if relevant)",
            "4. Source references (when configured to include sources)"
        ]
        
        if config.include_sources and aggregated_context.results:
            framework_parts.extend([
                "",
                "Source Citation Guidelines:",
                "• Reference specific sources when making claims",
                "• Use format: [Source X] for citations",
                "• Indicate confidence level when appropriate"
            ])
        
        return framework_header + "\\n" + "\\n".join(framework_parts)
    
    def _build_quality_instructions(self, config: ChatConfig) -> str:
        """Build quality assurance instructions."""
        quality_header = "=== QUALITY REQUIREMENTS ==="
        
        quality_requirements = [
            "Ensure your response:",
            "✓ CRITICAL: You MUST NOT hallucinate or make up any information. Only use facts from the provided context.",
            "✓ CRITICAL: If the context does not contain enough information to answer the question, explicitly state: 'I don't have enough information in the provided context to answer this question.'",
            "✓ CRITICAL: Do not infer, assume, or extrapolate beyond what is explicitly stated in the context.",
            "✓ CRITICAL: Every statement you make must be directly traceable to the provided context, conversation history, or recent transcripts.",
            "✓ When uncertain, always express doubt rather than guessing.",
            "✓ Directly addresses the user's question using ONLY the available information",
            "✓ Makes effective use of provided context without adding external knowledge",
            "✓ Maintains strict factual accuracy based on available data",
            "✓ Is coherent and well-structured",
            "✓ Matches the requested style and tone",
            "✓ Provides appropriate level of detail from available information",
            "✓ Clearly distinguishes between what you know from context and what you cannot determine"
        ]
        
        return quality_header + "\n" + "\n".join(quality_requirements)
    
    def _build_transcript_section(self, recent_transcripts: List[str]) -> str:
        """Build the recent transcripts section."""
        header = "=== RECENT AUDIO TRANSCRIPTS (LAST 12 HOURS) ==="
        if not recent_transcripts:
            return ""
        
        transcripts_summary = "\n".join([f"- {t[:200]}..." for t in recent_transcripts])
        return f"{header}\n{transcripts_summary}"
    
    def _get_confidence_indicator(self, score: float) -> str:
        """Get confidence indicator based on score."""
        if score >= 0.8:
            return "[HIGH CONFIDENCE]"
        elif score >= 0.6:
            return "[MODERATE CONFIDENCE]"
        elif score >= 0.4:
            return "[LOW CONFIDENCE]"
        else:
            return "[VERY LOW CONFIDENCE]"
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for context display."""
        relevant_fields = ['timestamp', 'audio_id', 'language', 'tags', 'category']
        formatted_parts = []
        
        for field in relevant_fields:
            if field in metadata and metadata[field]:
                formatted_parts.append(f"{field}: {metadata[field]}")
        
        return " | ".join(formatted_parts) if formatted_parts else "No additional context"
    
    def _build_fallback_prompt(self,
                              user_message: str,
                              aggregated_context: AggregatedContext,
                              config: ChatConfig) -> str:
        """Build fallback prompt when intelligent building fails."""
        try:
            logger.info("Building fallback prompt due to error in main prompt building")
            
            fallback_parts = [
                "You are a helpful AI assistant. Please respond to the user's question using any available context.",
                "",
                f"User Question: {user_message}"
            ]
            
            # Safely add context if available
            try:
                if aggregated_context and hasattr(aggregated_context, 'results') and aggregated_context.results:
                    context_items = []
                    for result in aggregated_context.results[:3]:
                        try:
                            if hasattr(result, 'content') and result.content:
                                content_preview = str(result.content)[:100]
                                context_items.append(f"- {content_preview}...")
                        except Exception as e:
                            logger.error(f"Error processing context result: {e}")
                            continue
                    
                    if context_items:
                        fallback_parts.extend([
                            "",
                            "Available Context:",
                            "\\n".join(context_items)
                        ])
            except Exception as e:
                logger.error(f"Error adding context to fallback prompt: {e}")
            
            fallback_parts.append("\\nPlease provide a helpful, accurate response.")
            
            return "\\n".join(fallback_parts)
            
        except Exception as e:
            logger.error(f"Error even in fallback prompt building: {e}", exc_info=True)
            # Ultra-minimal fallback
            return f"Please respond to: {user_message}"
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load pre-defined prompt templates."""
        return {
            "system_base": "You are an advanced AI assistant with comprehensive contextual knowledge.",
            "context_intro": "Based on the following relevant information:",
            "task_intro": "Your task is to:",
            "quality_footer": "Ensure accuracy, relevance, and helpfulness in your response."
        }


# Global instance
_prompt_builder: Optional[IntelligentPromptBuilder] = None

def get_intelligent_prompt_builder() -> IntelligentPromptBuilder:
    """Get the global intelligent prompt builder instance."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = IntelligentPromptBuilder()
    return _prompt_builder