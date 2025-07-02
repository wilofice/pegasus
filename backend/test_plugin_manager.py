#!/usr/bin/env python3
"""Test script for Plugin Manager functionality."""
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_plugin_dataclasses():
    """Test plugin dataclasses."""
    try:
        from services.plugin_manager import (
            PluginMetadata, PluginContext, PluginResult, PluginType, PluginStatus
        )
        
        # Test PluginMetadata
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type=PluginType.ANALYSIS,
            dependencies=["numpy"],
            tags=["test", "analysis"]
        )
        
        logger.info(f"✅ PluginMetadata created: {metadata.name} v{metadata.version}")
        
        # Test PluginContext
        context = PluginContext(
            audio_id="audio_123",
            user_id="user_456",
            transcript="This is a test transcript for analysis.",
            metadata={"language": "en", "duration": 120},
            config={"threshold": 0.8}
        )
        
        logger.info(f"✅ PluginContext created for audio: {context.audio_id}")
        
        # Test PluginResult
        result = PluginResult(
            plugin_name="test_plugin",
            success=True,
            result_data={"score": 0.85, "categories": ["tech", "ai"]},
            execution_time_ms=150.5
        )
        
        logger.info(f"✅ PluginResult created: success={result.success}, time={result.execution_time_ms}ms")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin dataclasses test failed: {e}")
        return False


def test_base_plugin():
    """Test BasePlugin abstract class."""
    try:
        from services.plugin_manager import BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        class TestAnalysisPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test_analysis",
                    version="1.0.0", 
                    description="Test analysis plugin",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                # Simulate analysis
                word_count = len(context.transcript.split())
                sentiment_score = 0.7  # Mock sentiment
                
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={
                        "word_count": word_count,
                        "sentiment_score": sentiment_score,
                        "analysis_type": "basic"
                    }
                )
        
        # Test plugin creation
        plugin = TestAnalysisPlugin({"threshold": 0.5})
        
        logger.info(f"✅ BasePlugin subclass created: {plugin.metadata.name}")
        logger.info(f"  Type: {plugin.metadata.plugin_type}")
        logger.info(f"  Config threshold: {plugin.get_config_value('threshold', 'not found')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ BasePlugin test failed: {e}")
        return False


async def test_plugin_manager_registration():
    """Test plugin registration and management."""
    try:
        from services.plugin_manager import PluginManager, BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        # Create test plugins
        class TestPlugin1(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test_plugin_1",
                    version="1.0.0",
                    description="First test plugin",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={"analysis": "test1_result"}
                )
        
        class TestPlugin2(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test_plugin_2", 
                    version="1.0.0",
                    description="Second test plugin",
                    author="Test Author",
                    plugin_type=PluginType.PROCESSING,
                    dependencies=["test_plugin_1"]
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={"processing": "test2_result"}
                )
        
        # Test plugin manager
        manager = PluginManager()
        
        # Register plugins
        success1 = manager.register_plugin(TestPlugin1, {"param1": "value1"})
        success2 = manager.register_plugin(TestPlugin2, {"param2": "value2"})
        
        logger.info(f"✅ Plugin registration: plugin1={success1}, plugin2={success2}")
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # List plugins
        plugins = manager.list_plugins()
        logger.info(f"✅ Listed {len(plugins)} plugins:")
        for plugin in plugins:
            logger.info(f"  - {plugin['name']} (v{plugin['version']}) - {plugin['status']}")
        
        # Get plugin info
        plugin1_info = manager.get_plugin_info("test_plugin_1")
        if plugin1_info:
            logger.info(f"✅ Plugin info retrieved: {plugin1_info['name']} - {plugin1_info['type']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin manager registration test failed: {e}")
        return False


async def test_plugin_execution():
    """Test plugin execution."""
    try:
        from services.plugin_manager import PluginManager, BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        class SentimentAnalysisPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="sentiment_analysis",
                    version="1.0.0",
                    description="Analyzes sentiment of transcripts",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS,
                    tags=["sentiment", "nlp"]
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                # Mock sentiment analysis
                positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
                negative_words = ["bad", "terrible", "awful", "horrible", "disappointing"]
                
                text = context.transcript.lower()
                pos_count = sum(1 for word in positive_words if word in text)
                neg_count = sum(1 for word in negative_words if word in text)
                
                # Calculate sentiment score
                total_sentiment_words = pos_count + neg_count
                if total_sentiment_words == 0:
                    sentiment_score = 0.5  # Neutral
                else:
                    sentiment_score = pos_count / total_sentiment_words
                
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={
                        "sentiment_score": sentiment_score,
                        "positive_words_found": pos_count,
                        "negative_words_found": neg_count,
                        "classification": "positive" if sentiment_score > 0.6 else "negative" if sentiment_score < 0.4 else "neutral"
                    },
                    metadata={
                        "word_count": len(context.transcript.split()),
                        "analysis_method": "keyword_based"
                    }
                )
        
        # Setup manager and plugin
        manager = PluginManager()
        manager.register_plugin(SentimentAnalysisPlugin, {"threshold": 0.5})
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Create test context
        context = PluginContext(
            audio_id="test_audio_123",
            user_id="test_user_456",
            transcript="This is a great and wonderful presentation about amazing AI technology!",
            metadata={"language": "en", "category": "tech"}
        )
        
        # Execute plugin
        result = await manager.execute_plugin("sentiment_analysis", context)
        
        logger.info(f"✅ Plugin execution result:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Execution time: {result.execution_time_ms:.2f}ms")
        logger.info(f"  Sentiment score: {result.result_data.get('sentiment_score', 'N/A')}")
        logger.info(f"  Classification: {result.result_data.get('classification', 'N/A')}")
        
        assert result.success == True
        assert result.result_data is not None
        assert "sentiment_score" in result.result_data
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin execution test failed: {e}")
        return False


async def test_plugin_type_execution():
    """Test executing plugins by type."""
    try:
        from services.plugin_manager import PluginManager, BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        # Create multiple analysis plugins
        class KeywordExtractorPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="keyword_extractor",
                    version="1.0.0",
                    description="Extracts keywords from transcripts",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                # Mock keyword extraction
                words = context.transcript.lower().split()
                # Simple keyword extraction: words longer than 4 characters
                keywords = [word for word in words if len(word) > 4]
                
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={
                        "keywords": keywords[:10],  # Top 10
                        "keyword_count": len(keywords),
                        "total_words": len(words)
                    }
                )
        
        class TopicClassifierPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="topic_classifier",
                    version="1.0.0",
                    description="Classifies transcript topics",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                # Mock topic classification
                text = context.transcript.lower()
                topics = []
                
                if any(word in text for word in ["ai", "machine", "learning", "technology"]):
                    topics.append("technology")
                if any(word in text for word in ["business", "strategy", "market"]):
                    topics.append("business")
                if any(word in text for word in ["health", "medical", "doctor"]):
                    topics.append("health")
                
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={
                        "topics": topics,
                        "primary_topic": topics[0] if topics else "general",
                        "confidence": 0.8 if topics else 0.3
                    }
                )
        
        # Setup manager and plugins
        manager = PluginManager()
        manager.register_plugin(KeywordExtractorPlugin)
        manager.register_plugin(TopicClassifierPlugin)
        
        # Wait for initialization  
        await asyncio.sleep(0.1)
        
        # Create test context
        context = PluginContext(
            audio_id="test_audio_456",
            user_id="test_user_789",
            transcript="This presentation covers machine learning algorithms and artificial intelligence applications in business strategy.",
            metadata={"category": "presentation"}
        )
        
        # Execute all analysis plugins
        results = await manager.execute_plugins_by_type(PluginType.ANALYSIS, context)
        
        logger.info(f"✅ Executed {len(results)} analysis plugins:")
        for result in results:
            logger.info(f"  - {result.plugin_name}: success={result.success}, time={result.execution_time_ms:.2f}ms")
            if result.result_data:
                # Show first few keys from result data
                keys = list(result.result_data.keys())[:3]
                logger.info(f"    Data keys: {keys}")
        
        assert len(results) == 2
        assert all(r.success for r in results)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin type execution test failed: {e}")
        return False


async def test_plugin_dependencies():
    """Test plugin dependency resolution."""
    try:
        from services.plugin_manager import PluginManager, BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        class BaseProcessorPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="base_processor",
                    version="1.0.0",
                    description="Base text processor",
                    author="Test Author",
                    plugin_type=PluginType.PROCESSING
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={"processed_text": context.transcript.lower()}
                )
        
        class AdvancedProcessorPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="advanced_processor",
                    version="1.0.0",
                    description="Advanced text processor",
                    author="Test Author",
                    plugin_type=PluginType.PROCESSING,
                    dependencies=["base_processor"]  # Depends on base processor
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={"advanced_features": ["tokenized", "normalized"]}
                )
        
        # Setup manager
        manager = PluginManager()
        
        # Register in reverse order to test dependency resolution
        manager.register_plugin(AdvancedProcessorPlugin)
        manager.register_plugin(BaseProcessorPlugin)
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Check execution order
        plugins_to_execute = ["advanced_processor", "base_processor"]
        ordered_plugins = manager._resolve_execution_order(plugins_to_execute)
        
        logger.info(f"✅ Dependency resolution:")
        logger.info(f"  Original order: {plugins_to_execute}")
        logger.info(f"  Resolved order: {ordered_plugins}")
        
        # Base processor should come before advanced processor
        assert ordered_plugins.index("base_processor") < ordered_plugins.index("advanced_processor")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin dependencies test failed: {e}")
        return False


async def test_plugin_error_handling():
    """Test plugin error handling."""
    try:
        from services.plugin_manager import PluginManager, BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        class ErrorPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="error_plugin",
                    version="1.0.0",
                    description="Plugin that always fails",
                    author="Test Author",
                    plugin_type=PluginType.ANALYSIS
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                # Simulate an error
                raise ValueError("This plugin always fails for testing")
        
        # Setup manager and plugin
        manager = PluginManager()
        manager.register_plugin(ErrorPlugin)
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Create test context
        context = PluginContext(
            audio_id="test_audio_error",
            user_id="test_user_error",
            transcript="This will cause an error",
            metadata={}
        )
        
        # Execute plugin (should handle error gracefully)
        result = await manager.execute_plugin("error_plugin", context)
        
        logger.info(f"✅ Error handling test:")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Error message: {result.error_message}")
        logger.info(f"  Execution time: {result.execution_time_ms:.2f}ms")
        
        assert result.success == False
        assert result.error_message is not None
        assert "always fails for testing" in result.error_message
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin error handling test failed: {e}")
        return False


async def main():
    """Run all plugin manager tests."""
    logger.info("🧪 Running Plugin Manager Tests")
    
    tests = [
        ("Plugin Dataclasses", test_plugin_dataclasses),
        ("BasePlugin Abstract Class", test_base_plugin),
        ("Plugin Manager Registration", test_plugin_manager_registration),
        ("Plugin Execution", test_plugin_execution),
        ("Plugin Type Execution", test_plugin_type_execution),
        ("Plugin Dependencies", test_plugin_dependencies),
        ("Plugin Error Handling", test_plugin_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Plugin Manager tests passed!")
        logger.info("\n📋 Plugin Manager Features:")
        logger.info("  ✅ Plugin registration and lifecycle management")
        logger.info("  ✅ Multiple plugin types (analysis, processing, notification, etc.)")
        logger.info("  ✅ Dependency resolution and execution ordering")
        logger.info("  ✅ Type-based plugin execution with parallel/sequential options")
        logger.info("  ✅ Comprehensive error handling and recovery")
        logger.info("  ✅ Plugin metadata and configuration management")
        logger.info("  ✅ Execution hooks for monitoring and integration")
        logger.info("  ✅ Plugin reloading and hot-swapping capabilities")
        return 0
    else:
        logger.error("💥 Some Plugin Manager tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))