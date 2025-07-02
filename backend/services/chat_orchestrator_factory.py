"""Factory for creating Chat Orchestrator V2 instances with real services."""
import logging
from typing import Optional

from services.chat_orchestrator_v2 import ChatOrchestratorV2, ChatConfig, ConversationMode, ResponseStyle
from services.context_aggregator_factory import get_context_aggregator
from services.plugin_manager import PluginManager, get_plugin_manager
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class ChatOrchestratorFactory:
    """Factory for creating and configuring Chat Orchestrator V2 instances."""
    
    @staticmethod
    async def create_default_orchestrator(
        context_aggregator_profile: str = "balanced",
        enable_plugins: bool = True,
        enable_local_llm: bool = False
    ) -> ChatOrchestratorV2:
        """Create a Chat Orchestrator V2 with default services.
        
        Args:
            context_aggregator_profile: Context aggregator optimization profile
            enable_plugins: Whether to enable plugin system
            enable_local_llm: Whether to enable local Ollama LLM
            
        Returns:
            Configured ChatOrchestratorV2 instance
        """
        try:
            logger.info("Creating Chat Orchestrator V2 with default services...")
            
            # Create context aggregator
            context_aggregator = await get_context_aggregator(context_aggregator_profile)
            
            # Create plugin manager if enabled
            plugin_manager = None
            if enable_plugins:
                try:
                    plugin_manager = await get_plugin_manager()
                    logger.info("Plugin manager created successfully")
                except Exception as e:
                    logger.warning(f"Plugin manager creation failed: {e}")
            
            # Create Ollama service if enabled
            ollama_service = None
            if enable_local_llm:
                try:
                    ollama_service = OllamaService()
                    await ollama_service.health_check()
                    logger.info("Ollama service created successfully")
                except Exception as e:
                    logger.warning(f"Ollama service creation failed: {e}")
            
            # Create default configuration
            default_config = ChatConfig(
                enable_plugins=enable_plugins,
                use_local_llm=enable_local_llm and ollama_service is not None
            )
            
            # Create orchestrator
            orchestrator = ChatOrchestratorV2(
                context_aggregator=context_aggregator,
                plugin_manager=plugin_manager,
                ollama_service=ollama_service,
                default_config=default_config
            )
            
            logger.info("Chat Orchestrator V2 created successfully")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Failed to create Chat Orchestrator V2: {e}")
            raise
    
    @staticmethod
    async def create_research_orchestrator() -> ChatOrchestratorV2:
        """Create an orchestrator optimized for research and analysis."""
        try:
            orchestrator = await ChatOrchestratorFactory.create_default_orchestrator(
                context_aggregator_profile="accuracy",
                enable_plugins=True,
                enable_local_llm=False
            )
            
            # Override config for research mode
            orchestrator.default_config = ChatConfig(
                max_context_results=25,  # More context for research
                conversation_mode=ConversationMode.RESEARCH,
                response_style=ResponseStyle.DETAILED,
                include_sources=True,
                include_confidence=True,
                enable_plugins=True,
                max_tokens=1500,  # Longer responses
                temperature=0.3   # More focused responses
            )
            
            logger.info("Research-optimized Chat Orchestrator V2 created")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Failed to create research orchestrator: {e}")
            raise
    
    @staticmethod
    async def create_conversational_orchestrator() -> ChatOrchestratorV2:
        """Create an orchestrator optimized for casual conversation."""
        try:
            orchestrator = await ChatOrchestratorFactory.create_default_orchestrator(
                context_aggregator_profile="speed",
                enable_plugins=False,  # Faster without plugins
                enable_local_llm=True
            )
            
            # Override config for conversational mode
            orchestrator.default_config = ChatConfig(
                max_context_results=10,  # Less context for speed
                conversation_mode=ConversationMode.CONVERSATIONAL,
                response_style=ResponseStyle.CASUAL,
                include_sources=False,  # Cleaner conversation
                include_confidence=False,
                enable_plugins=False,
                max_tokens=800,   # Shorter responses
                temperature=0.8   # More creative responses
            )
            
            logger.info("Conversational-optimized Chat Orchestrator V2 created")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Failed to create conversational orchestrator: {e}")
            raise
    
    @staticmethod
    async def create_analytical_orchestrator() -> ChatOrchestratorV2:
        """Create an orchestrator optimized for analytical tasks."""
        try:
            orchestrator = await ChatOrchestratorFactory.create_default_orchestrator(
                context_aggregator_profile="accuracy",
                enable_plugins=True,
                enable_local_llm=False
            )
            
            # Override config for analytical mode
            orchestrator.default_config = ChatConfig(
                max_context_results=20,
                conversation_mode=ConversationMode.ANALYTICAL,
                response_style=ResponseStyle.PROFESSIONAL,
                include_sources=True,
                include_confidence=True,
                enable_plugins=True,
                max_tokens=1200,
                temperature=0.2   # Very focused responses
            )
            
            logger.info("Analytical-optimized Chat Orchestrator V2 created")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Failed to create analytical orchestrator: {e}")
            raise
    
    @staticmethod
    async def create_custom_orchestrator(
        context_config: dict,
        chat_config: dict,
        services_config: dict
    ) -> ChatOrchestratorV2:
        """Create a fully customized Chat Orchestrator V2.
        
        Args:
            context_config: Context aggregator configuration
            chat_config: Chat orchestrator configuration
            services_config: Services configuration (plugins, ollama, etc.)
            
        Returns:
            Customized ChatOrchestratorV2 instance
        """
        try:
            # Create context aggregator
            aggregator_profile = context_config.get("profile", "balanced")
            context_aggregator = await get_context_aggregator(aggregator_profile)
            
            # Create plugin manager if requested
            plugin_manager = None
            if services_config.get("enable_plugins", False):
                try:
                    plugin_manager = await get_plugin_manager()
                except Exception as e:
                    logger.warning(f"Plugin manager creation failed: {e}")
            
            # Create Ollama service if requested
            ollama_service = None
            if services_config.get("enable_local_llm", False):
                try:
                    ollama_service = OllamaService()
                except Exception as e:
                    logger.warning(f"Ollama service creation failed: {e}")
            
            # Create custom chat config
            config = ChatConfig(**chat_config)
            
            # Create orchestrator
            orchestrator = ChatOrchestratorV2(
                context_aggregator=context_aggregator,
                plugin_manager=plugin_manager,
                ollama_service=ollama_service,
                default_config=config
            )
            
            logger.info("Custom Chat Orchestrator V2 created successfully")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Failed to create custom orchestrator: {e}")
            raise


# Convenience functions for easy access
async def get_chat_orchestrator(profile: str = "default") -> ChatOrchestratorV2:
    """Get a Chat Orchestrator V2 instance with specified profile.
    
    Args:
        profile: Orchestrator profile ('default', 'research', 'conversational', 'analytical')
        
    Returns:
        ChatOrchestratorV2 instance
    """
    if profile == "research":
        return await ChatOrchestratorFactory.create_research_orchestrator()
    elif profile == "conversational":
        return await ChatOrchestratorFactory.create_conversational_orchestrator()
    elif profile == "analytical":
        return await ChatOrchestratorFactory.create_analytical_orchestrator()
    else:
        return await ChatOrchestratorFactory.create_default_orchestrator()


async def get_default_chat_orchestrator() -> ChatOrchestratorV2:
    """Get default Chat Orchestrator V2 instance."""
    return await ChatOrchestratorFactory.create_default_orchestrator()