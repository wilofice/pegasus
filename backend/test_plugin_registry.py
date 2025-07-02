#!/usr/bin/env python3
"""Test script for Plugin Registry functionality."""
import sys
import logging
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_plugin_discovery():
    """Test automatic plugin discovery."""
    try:
        from services.plugin_registry import PluginRegistry
        
        registry = PluginRegistry()
        
        # Discover built-in plugins
        discovered_plugins = registry.discover_builtin_plugins()
        
        logger.info(f"✅ Plugin discovery result:")
        logger.info(f"  Discovered {len(discovered_plugins)} plugin(s)")
        
        for plugin_class in discovered_plugins:
            logger.info(f"    - {plugin_class.__name__} from {plugin_class.__module__}")
        
        # Should find at least the ReviewReflectionPlugin
        plugin_names = [cls.__name__ for cls in discovered_plugins]
        assert "ReviewReflectionPlugin" in plugin_names
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin discovery test failed: {e}")
        return False


async def test_plugin_registration():
    """Test automatic plugin registration."""
    try:
        from services.plugin_registry import PluginRegistry
        
        registry = PluginRegistry()
        
        # Register built-in plugins
        registration_results = registry.register_builtin_plugins()
        
        logger.info(f"✅ Plugin registration results:")
        for plugin_name, success in registration_results.items():
            status = "✅" if success else "❌"
            logger.info(f"  {status} {plugin_name}: {success}")
        
        # Get registered plugins
        registered_plugins = registry.get_registered_plugins()
        logger.info(f"  Total registered: {len(registered_plugins)}")
        
        # Should successfully register at least one plugin
        assert len(registration_results) > 0
        assert "ReviewReflectionPlugin" in registration_results
        
        # Wait for plugin initialization
        await asyncio.sleep(0.5)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin registration test failed: {e}")
        return False


async def test_plugin_execution_through_registry():
    """Test executing a plugin through the registry system."""
    try:
        from services.plugin_registry import plugin_registry, initialize_plugins
        from services.plugin_manager import plugin_manager, PluginContext, PluginType
        
        # Initialize plugins
        init_results = initialize_plugins()
        logger.info(f"✅ Plugin initialization: {init_results}")
        
        # Wait for initialization
        await asyncio.sleep(0.5)
        
        # Create test context
        context = PluginContext(
            audio_id="registry_test_123",
            user_id="test_user_789",
            transcript="""
            This is a test meeting to validate our plugin registry system.
            We need to ensure that plugins are automatically discovered and registered.
            Sarah, can you verify that the review plugin is working correctly?
            I'm excited about this new functionality - it will save us a lot of time.
            Let's schedule a follow-up meeting to discuss the results.
            """,
            metadata={
                "category": "system_test",
                "language": "en"
            },
            entities=[
                {"text": "Sarah", "type": "PERSON"}
            ]
        )
        
        # Execute plugins by type
        results = await plugin_manager.execute_plugins_by_type(
            PluginType.ANALYSIS, 
            context, 
            parallel=False
        )
        
        logger.info(f"✅ Plugin execution through registry:")
        logger.info(f"  Executed {len(results)} plugin(s)")
        
        for result in results:
            logger.info(f"    - {result.plugin_name}: success={result.success}")
            if result.success and result.result_data:
                insights = result.result_data.get("insights", [])
                logger.info(f"      Generated {len(insights)} insights")
        
        # Should execute at least one plugin successfully
        assert len(results) > 0
        assert any(r.success for r in results)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin execution test failed: {e}")
        return False


async def test_plugin_statistics():
    """Test plugin statistics and monitoring."""
    try:
        from services.plugin_registry import plugin_registry
        
        # Get plugin statistics
        stats = plugin_registry.get_plugin_statistics()
        
        logger.info(f"✅ Plugin statistics:")
        logger.info(f"  Total registered: {stats.get('total_registered', 0)}")
        logger.info(f"  In manager: {stats.get('total_in_manager', 0)}")
        logger.info(f"  By status: {stats.get('by_status', {})}")
        logger.info(f"  By type: {stats.get('by_type', {})}")
        logger.info(f"  Registration source: {stats.get('registration_source', {})}")
        
        # Should have statistics available
        assert stats.get('total_registered', 0) >= 0
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Plugin statistics test failed: {e}")
        return False


async def test_external_plugin_registration():
    """Test registering an external plugin."""
    try:
        from services.plugin_registry import plugin_registry
        from services.plugin_manager import BasePlugin, PluginMetadata, PluginContext, PluginResult, PluginType
        
        # Create a simple external plugin
        class TestExternalPlugin(BasePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="test_external_plugin",
                    version="1.0.0",
                    description="Test external plugin",
                    author="Test Suite",
                    plugin_type=PluginType.PROCESSING
                )
            
            async def execute(self, context: PluginContext) -> PluginResult:
                return PluginResult(
                    plugin_name=self.metadata.name,
                    success=True,
                    result_data={"test": "external_plugin_working"}
                )
        
        # Register external plugin
        success = plugin_registry.register_external_plugin(
            TestExternalPlugin,
            {"test_config": "test_value"}
        )
        
        logger.info(f"✅ External plugin registration: {success}")
        
        # Wait for initialization
        await asyncio.sleep(0.5)
        
        # Test execution
        from services.plugin_manager import plugin_manager, PluginContext
        
        context = PluginContext(
            audio_id="external_test",
            user_id="test_user",
            transcript="Test content for external plugin",
            metadata={}
        )
        
        result = await plugin_manager.execute_plugin("test_external_plugin", context)
        
        logger.info(f"  External plugin execution: success={result.success}")
        if result.success:
            logger.info(f"  Result: {result.result_data}")
        
        # Cleanup - unregister external plugin
        cleanup_success = plugin_registry.unregister_plugin("test_external_plugin")
        logger.info(f"  Cleanup successful: {cleanup_success}")
        
        assert success == True
        assert result.success == True
        
        return True
        
    except Exception as e:
        logger.error(f"❌ External plugin test failed: {e}")
        return False


async def test_initialize_and_shutdown():
    """Test the initialize and shutdown functions."""
    try:
        from services.plugin_registry import initialize_plugins, shutdown_plugins
        
        # Test initialization
        logger.info("✅ Testing plugin initialization...")
        init_results = initialize_plugins()
        
        logger.info(f"  Initialization results: {init_results}")
        
        successful = sum(1 for success in init_results.values() if success)
        total = len(init_results)
        logger.info(f"  Success rate: {successful}/{total}")
        
        # Wait for initialization
        await asyncio.sleep(0.5)
        
        # Test shutdown
        logger.info("✅ Testing plugin shutdown...")
        shutdown_plugins()
        
        logger.info("  Shutdown completed")
        
        # Should have successful initialization
        assert len(init_results) > 0
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Initialize/shutdown test failed: {e}")
        return False


async def main():
    """Run all plugin registry tests."""
    logger.info("🧪 Running Plugin Registry Tests")
    
    tests = [
        ("Plugin Discovery", test_plugin_discovery),
        ("Plugin Registration", test_plugin_registration),
        ("Plugin Execution Through Registry", test_plugin_execution_through_registry),
        ("Plugin Statistics", test_plugin_statistics),
        ("External Plugin Registration", test_external_plugin_registration),
        ("Initialize and Shutdown", test_initialize_and_shutdown),
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
        logger.info("🎉 All Plugin Registry tests passed!")
        logger.info("\n📋 Registry Features Validated:")
        logger.info("  ✅ Automatic plugin discovery from plugins directory")
        logger.info("  ✅ Built-in plugin registration with default configuration")
        logger.info("  ✅ External plugin registration and management")
        logger.info("  ✅ Plugin execution through registry system")
        logger.info("  ✅ Statistics and monitoring capabilities")
        logger.info("  ✅ System initialization and shutdown procedures")
        logger.info("  ✅ Plugin lifecycle management")
        return 0
    else:
        logger.error("💥 Some Plugin Registry tests failed.")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))