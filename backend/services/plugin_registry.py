"""Plugin registry for automatic discovery and registration of plugins."""
import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Type, Any

from services.plugin_manager import BasePlugin, plugin_manager

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for discovering and registering plugins."""
    
    def __init__(self):
        """Initialize plugin registry."""
        self.registered_plugins: Dict[str, Type[BasePlugin]] = {}
    
    def discover_builtin_plugins(self) -> List[Type[BasePlugin]]:
        """Discover built-in plugins from the plugins directory.
        
        Returns:
            List of discovered plugin classes
        """
        discovered_plugins = []
        
        try:
            # Get the plugins directory
            plugins_dir = Path(__file__).parent.parent / "plugins"
            
            if not plugins_dir.exists():
                logger.warning("Plugins directory not found")
                return discovered_plugins
            
            # Scan for Python files in plugins directory
            for plugin_file in plugins_dir.glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue
                
                try:
                    # Import the module
                    module_name = f"plugins.{plugin_file.stem}"
                    module = importlib.import_module(module_name)
                    
                    # Look for BasePlugin subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, BasePlugin) and 
                            obj != BasePlugin and 
                            obj.__module__ == module_name):
                            
                            discovered_plugins.append(obj)
                            logger.info(f"Discovered plugin class: {name} in {module_name}")
                
                except Exception as e:
                    logger.error(f"Error importing plugin from {plugin_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error discovering plugins: {e}")
        
        return discovered_plugins
    
    def register_builtin_plugins(self) -> Dict[str, bool]:
        """Register all discovered built-in plugins.
        
        Returns:
            Dictionary mapping plugin names to registration success
        """
        registration_results = {}
        
        try:
            # Discover plugins
            discovered_plugins = self.discover_builtin_plugins()
            
            if not discovered_plugins:
                logger.info("No built-in plugins found to register")
                return registration_results
            
            # Register each plugin
            for plugin_class in discovered_plugins:
                try:
                    # Get default configuration for the plugin
                    config = self._get_default_config(plugin_class)
                    
                    # Register with plugin manager
                    success = plugin_manager.register_plugin(
                        plugin_class,
                        config=config,
                        auto_initialize=True
                    )
                    
                    plugin_name = plugin_class.__name__
                    registration_results[plugin_name] = success
                    
                    if success:
                        self.registered_plugins[plugin_name] = plugin_class
                        logger.info(f"Successfully registered plugin: {plugin_name}")
                    else:
                        logger.error(f"Failed to register plugin: {plugin_name}")
                
                except Exception as e:
                    plugin_name = getattr(plugin_class, '__name__', 'Unknown')
                    logger.error(f"Error registering plugin {plugin_name}: {e}")
                    registration_results[plugin_name] = False
        
        except Exception as e:
            logger.error(f"Error during plugin registration: {e}")
        
        return registration_results
    
    def _get_default_config(self, plugin_class: Type[BasePlugin]) -> Dict[str, Any]:
        """Get default configuration for a plugin class.
        
        Args:
            plugin_class: Plugin class to get config for
            
        Returns:
            Default configuration dictionary
        """
        try:
            # Create temporary instance to get metadata
            temp_instance = plugin_class()
            metadata = temp_instance.metadata
            
            # Extract default values from config schema
            config = {}
            if metadata.config_schema and 'properties' in metadata.config_schema:
                for prop_name, prop_config in metadata.config_schema['properties'].items():
                    if 'default' in prop_config:
                        config[prop_name] = prop_config['default']
            
            return config
        
        except Exception as e:
            logger.warning(f"Could not get default config for {plugin_class.__name__}: {e}")
            return {}
    
    def get_registered_plugins(self) -> Dict[str, Type[BasePlugin]]:
        """Get all registered plugin classes.
        
        Returns:
            Dictionary mapping plugin names to plugin classes
        """
        return self.registered_plugins.copy()
    
    def register_external_plugin(
        self, 
        plugin_class: Type[BasePlugin], 
        config: Dict[str, Any] = None
    ) -> bool:
        """Register an external plugin class.
        
        Args:
            plugin_class: External plugin class to register
            config: Plugin configuration
            
        Returns:
            True if registration successful
        """
        try:
            success = plugin_manager.register_plugin(
                plugin_class,
                config=config or {},
                auto_initialize=True
            )
            
            if success:
                plugin_name = plugin_class.__name__
                self.registered_plugins[plugin_name] = plugin_class
                logger.info(f"Successfully registered external plugin: {plugin_name}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error registering external plugin: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin.
        
        Args:
            plugin_name: Name of plugin to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            success = plugin_manager.unregister_plugin(plugin_name)
            
            if success and plugin_name in self.registered_plugins:
                del self.registered_plugins[plugin_name]
                logger.info(f"Successfully unregistered plugin: {plugin_name}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error unregistering plugin {plugin_name}: {e}")
            return False
    
    def reload_all_plugins(self) -> Dict[str, bool]:
        """Reload all registered plugins.
        
        Returns:
            Dictionary mapping plugin names to reload success
        """
        reload_results = {}
        
        for plugin_name in list(self.registered_plugins.keys()):
            try:
                # Get current plugin class and config
                plugin_class = self.registered_plugins[plugin_name]
                current_config = self._get_default_config(plugin_class)
                
                # Unregister and re-register
                if self.unregister_plugin(plugin_name):
                    success = self.register_external_plugin(plugin_class, current_config)
                    reload_results[plugin_name] = success
                else:
                    reload_results[plugin_name] = False
            
            except Exception as e:
                logger.error(f"Error reloading plugin {plugin_name}: {e}")
                reload_results[plugin_name] = False
        
        return reload_results
    
    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered plugins.
        
        Returns:
            Plugin statistics dictionary
        """
        try:
            plugins_info = plugin_manager.list_plugins()
            
            stats = {
                "total_registered": len(self.registered_plugins),
                "total_in_manager": len(plugins_info),
                "by_status": {},
                "by_type": {},
                "registration_source": {
                    "builtin": 0,
                    "external": 0
                }
            }
            
            # Count by status and type
            for plugin_info in plugins_info:
                status = plugin_info['status']
                plugin_type = plugin_info['type']
                
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                stats["by_type"][plugin_type] = stats["by_type"].get(plugin_type, 0) + 1
            
            # Determine registration source (rough estimate)
            for plugin_name in self.registered_plugins:
                plugin_class = self.registered_plugins[plugin_name]
                if plugin_class.__module__.startswith('plugins.'):
                    stats["registration_source"]["builtin"] += 1
                else:
                    stats["registration_source"]["external"] += 1
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting plugin statistics: {e}")
            return {}


# Global plugin registry instance
plugin_registry = PluginRegistry()


def initialize_plugins() -> Dict[str, bool]:
    """Initialize and register all built-in plugins.
    
    This function should be called during application startup.
    
    Returns:
        Dictionary mapping plugin names to registration success
    """
    logger.info("Initializing Pegasus Brain plugins...")
    
    try:
        # Register built-in plugins
        results = plugin_registry.register_builtin_plugins()
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"Plugin initialization complete: {successful}/{total} plugins registered successfully")
        
        if successful < total:
            failed_plugins = [name for name, success in results.items() if not success]
            logger.warning(f"Failed to register plugins: {failed_plugins}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error during plugin initialization: {e}")
        return {}


def shutdown_plugins():
    """Shutdown all plugins and cleanup resources.
    
    This function should be called during application shutdown.
    """
    logger.info("Shutting down plugins...")
    
    try:
        # Shutdown plugin manager (will cleanup all plugins)
        import asyncio
        
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop:
            loop.run_until_complete(plugin_manager.shutdown())
        
        # Clear registry
        plugin_registry.registered_plugins.clear()
        
        logger.info("Plugin shutdown complete")
    
    except Exception as e:
        logger.error(f"Error during plugin shutdown: {e}")