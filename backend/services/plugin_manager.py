"""Plugin management system for extensible transcript analysis."""
import logging
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    """Plugin status enumeration."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


class PluginType(str, Enum):
    """Plugin type enumeration."""
    ANALYSIS = "analysis"
    PROCESSING = "processing"
    NOTIFICATION = "notification"
    EXPORT = "export"
    INTEGRATION = "integration"


@dataclass
class PluginMetadata:
    """Plugin metadata information."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    min_python_version: str = "3.8"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PluginContext:
    """Context passed to plugins during execution."""
    audio_id: str
    user_id: str
    transcript: str
    metadata: Dict[str, Any]
    chunks: Optional[List[Dict[str, Any]]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    related_context: Optional[List[Dict[str, Any]]] = None
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginResult:
    """Result returned by plugin execution."""
    plugin_name: str
    success: bool
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize plugin with configuration.
        
        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abstractmethod
    async def execute(self, context: PluginContext) -> PluginResult:
        """Execute the plugin with given context.
        
        Args:
            context: Plugin execution context
            
        Returns:
            PluginResult with execution results
        """
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        return True
    
    async def initialize(self) -> bool:
        """Initialize plugin resources.
        
        Returns:
            True if initialization successful
        """
        return True
    
    async def cleanup(self) -> bool:
        """Clean up plugin resources.
        
        Returns:
            True if cleanup successful
        """
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)


@dataclass
class RegisteredPlugin:
    """Information about a registered plugin."""
    plugin_class: Type[BasePlugin]
    instance: Optional[BasePlugin]
    metadata: PluginMetadata
    status: PluginStatus
    config: Dict[str, Any]
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class PluginManager:
    """Manager for plugin registration, loading, and execution."""
    
    def __init__(self):
        """Initialize plugin manager."""
        self._plugins: Dict[str, RegisteredPlugin] = {}
        self._execution_hooks: Dict[str, List[Callable]] = {
            "before_execution": [],
            "after_execution": [],
            "on_error": []
        }
        self._plugin_dependencies: Dict[str, List[str]] = {}
    
    def register_plugin(
        self,
        plugin_class: Type[BasePlugin],
        config: Dict[str, Any] = None,
        auto_initialize: bool = True
    ) -> bool:
        """Register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
            config: Plugin configuration
            auto_initialize: Whether to initialize plugin immediately
            
        Returns:
            True if registration successful
        """
        try:
            # Create temporary instance to get metadata
            temp_instance = plugin_class(config or {})
            metadata = temp_instance.metadata
            
            plugin_name = metadata.name
            
            if plugin_name in self._plugins:
                logger.warning(f"Plugin {plugin_name} already registered, updating...")
            
            # Create registered plugin entry
            registered_plugin = RegisteredPlugin(
                plugin_class=plugin_class,
                instance=None,
                metadata=metadata,
                status=PluginStatus.LOADING,
                config=config or {}
            )
            
            self._plugins[plugin_name] = registered_plugin
            
            # Track dependencies
            self._plugin_dependencies[plugin_name] = metadata.dependencies
            
            if auto_initialize:
                asyncio.create_task(self._initialize_plugin(plugin_name))
            
            logger.info(f"Registered plugin: {plugin_name} (v{metadata.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
            return False
    
    async def _initialize_plugin(self, plugin_name: str) -> bool:
        """Initialize a registered plugin.
        
        Args:
            plugin_name: Name of plugin to initialize
            
        Returns:
            True if initialization successful
        """
        try:
            registered_plugin = self._plugins[plugin_name]
            
            # Check dependencies
            for dep in registered_plugin.metadata.dependencies:
                if dep not in self._plugins or self._plugins[dep].status != PluginStatus.ENABLED:
                    raise ValueError(f"Dependency {dep} not available")
            
            # Create plugin instance
            instance = registered_plugin.plugin_class(registered_plugin.config)
            
            # Validate configuration
            if not await instance.validate_config(registered_plugin.config):
                raise ValueError("Plugin configuration validation failed")
            
            # Initialize plugin
            if not await instance.initialize():
                raise ValueError("Plugin initialization failed")
            
            # Update registration
            registered_plugin.instance = instance
            registered_plugin.status = PluginStatus.ENABLED
            registered_plugin.last_error = None
            registered_plugin.updated_at = datetime.utcnow()
            
            logger.info(f"Initialized plugin: {plugin_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize plugin {plugin_name}: {e}"
            logger.error(error_msg)
            
            if plugin_name in self._plugins:
                self._plugins[plugin_name].status = PluginStatus.ERROR
                self._plugins[plugin_name].last_error = str(e)
                
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin.
        
        Args:
            plugin_name: Name of plugin to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            if plugin_name not in self._plugins:
                logger.warning(f"Plugin {plugin_name} not registered")
                return False
            
            registered_plugin = self._plugins[plugin_name]
            
            # Cleanup plugin if it has an instance
            if registered_plugin.instance:
                asyncio.create_task(registered_plugin.instance.cleanup())
            
            # Remove from registry
            del self._plugins[plugin_name]
            del self._plugin_dependencies[plugin_name]
            
            logger.info(f"Unregistered plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister plugin {plugin_name}: {e}")
            return False
    
    async def execute_plugin(
        self,
        plugin_name: str,
        context: PluginContext
    ) -> PluginResult:
        """Execute a specific plugin.
        
        Args:
            plugin_name: Name of plugin to execute
            context: Execution context
            
        Returns:
            PluginResult with execution results
        """
        start_time = datetime.now()
        
        try:
            # Check if plugin exists and is enabled
            if plugin_name not in self._plugins:
                return PluginResult(
                    plugin_name=plugin_name,
                    success=False,
                    error_message=f"Plugin {plugin_name} not found"
                )
            
            registered_plugin = self._plugins[plugin_name]
            
            if registered_plugin.status != PluginStatus.ENABLED:
                return PluginResult(
                    plugin_name=plugin_name,
                    success=False,
                    error_message=f"Plugin {plugin_name} is not enabled (status: {registered_plugin.status})"
                )
            
            if not registered_plugin.instance:
                return PluginResult(
                    plugin_name=plugin_name,
                    success=False,
                    error_message=f"Plugin {plugin_name} instance not available"
                )
            
            # Add plugin config to context
            context.config.update(registered_plugin.config)
            
            # Execute before hooks
            await self._execute_hooks("before_execution", plugin_name, context)
            
            # Execute plugin
            result = await registered_plugin.instance.execute(context)
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            result.execution_time_ms = execution_time
            
            # Execute after hooks
            await self._execute_hooks("after_execution", plugin_name, context, result)
            
            logger.debug(f"Executed plugin {plugin_name} in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            error_msg = f"Plugin execution failed: {e}"
            logger.error(f"Error executing plugin {plugin_name}: {error_msg}")
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = PluginResult(
                plugin_name=plugin_name,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time
            )
            
            # Execute error hooks
            await self._execute_hooks("on_error", plugin_name, context, result, e)
            
            return result
    
    async def execute_plugins_by_type(
        self,
        plugin_type: PluginType,
        context: PluginContext,
        parallel: bool = False
    ) -> List[PluginResult]:
        """Execute all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to execute
            context: Execution context
            parallel: Whether to execute plugins in parallel
            
        Returns:
            List of PluginResult objects
        """
        # Get plugins of specified type
        plugins_to_execute = [
            name for name, plugin in self._plugins.items()
            if plugin.metadata.plugin_type == plugin_type and plugin.status == PluginStatus.ENABLED
        ]
        
        if not plugins_to_execute:
            logger.info(f"No enabled plugins found for type: {plugin_type}")
            return []
        
        # Sort by dependencies (topological sort)
        ordered_plugins = self._resolve_execution_order(plugins_to_execute)
        
        results = []
        
        if parallel:
            # Execute in parallel (ignoring dependencies for now)
            tasks = [self.execute_plugin(name, context) for name in ordered_plugins]
            results = await asyncio.gather(*tasks)
        else:
            # Execute sequentially
            for plugin_name in ordered_plugins:
                result = await self.execute_plugin(plugin_name, context)
                results.append(result)
        
        return results
    
    def _resolve_execution_order(self, plugin_names: List[str]) -> List[str]:
        """Resolve plugin execution order based on dependencies.
        
        Args:
            plugin_names: List of plugin names to order
            
        Returns:
            Ordered list of plugin names
        """
        # Simple topological sort implementation
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(plugin_name: str):
            if plugin_name in temp_visited:
                # Circular dependency detected
                logger.warning(f"Circular dependency detected involving {plugin_name}")
                return
            
            if plugin_name in visited:
                return
            
            temp_visited.add(plugin_name)
            
            # Visit dependencies first
            for dep in self._plugin_dependencies.get(plugin_name, []):
                if dep in plugin_names:
                    visit(dep)
            
            temp_visited.remove(plugin_name)
            visited.add(plugin_name)
            result.append(plugin_name)
        
        for plugin_name in plugin_names:
            if plugin_name not in visited:
                visit(plugin_name)
        
        return result
    
    async def _execute_hooks(self, hook_type: str, *args, **kwargs):
        """Execute registered hooks.
        
        Args:
            hook_type: Type of hook to execute
            *args: Hook arguments
            **kwargs: Hook keyword arguments
        """
        hooks = self._execution_hooks.get(hook_type, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook execution failed: {e}")
    
    def add_hook(self, hook_type: str, hook_func: Callable) -> bool:
        """Add an execution hook.
        
        Args:
            hook_type: Type of hook (before_execution, after_execution, on_error)
            hook_func: Hook function to add
            
        Returns:
            True if hook added successfully
        """
        if hook_type not in self._execution_hooks:
            logger.error(f"Invalid hook type: {hook_type}")
            return False
        
        self._execution_hooks[hook_type].append(hook_func)
        logger.info(f"Added {hook_type} hook: {hook_func.__name__}")
        return True
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered plugin.
        
        Args:
            plugin_name: Name of plugin
            
        Returns:
            Plugin information dictionary or None
        """
        if plugin_name not in self._plugins:
            return None
        
        plugin = self._plugins[plugin_name]
        return {
            "name": plugin.metadata.name,
            "version": plugin.metadata.version,
            "description": plugin.metadata.description,
            "author": plugin.metadata.author,
            "type": plugin.metadata.plugin_type.value,
            "status": plugin.status.value,
            "dependencies": plugin.metadata.dependencies,
            "tags": plugin.metadata.tags,
            "config": plugin.config,
            "last_error": plugin.last_error,
            "created_at": plugin.created_at.isoformat(),
            "updated_at": plugin.updated_at.isoformat()
        }
    
    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None
    ) -> List[Dict[str, Any]]:
        """List registered plugins with optional filtering.
        
        Args:
            plugin_type: Filter by plugin type
            status: Filter by plugin status
            
        Returns:
            List of plugin information dictionaries
        """
        plugins = []
        
        for plugin_name, plugin in self._plugins.items():
            # Apply filters
            if plugin_type and plugin.metadata.plugin_type != plugin_type:
                continue
            if status and plugin.status != status:
                continue
            
            plugin_info = self.get_plugin_info(plugin_name)
            if plugin_info:
                plugins.append(plugin_info)
        
        return sorted(plugins, key=lambda x: x['name'])
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin.
        
        Args:
            plugin_name: Name of plugin to reload
            
        Returns:
            True if reload successful
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin {plugin_name} not found")
            return False
        
        try:
            # Store current config
            current_config = self._plugins[plugin_name].config
            plugin_class = self._plugins[plugin_name].plugin_class
            
            # Unregister and re-register
            self.unregister_plugin(plugin_name)
            self.register_plugin(plugin_class, current_config, auto_initialize=True)
            
            logger.info(f"Reloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False
    
    async def process_message(self, 
                            message: str, 
                            context: Any = None, 
                            conversation_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a message through enabled plugins.
        
        Args:
            message: The chat message to process
            context: Context from the context aggregator
            conversation_context: Additional conversation metadata
            
        Returns:
            Dictionary of plugin results
        """
        try:
            # Create plugin context
            plugin_context = PluginContext(
                audio_id="chat_message",  # Placeholder for chat messages
                user_id=conversation_context.get("user_id", "unknown") if conversation_context else "unknown",
                transcript=message,
                metadata=conversation_context or {},
                chunks=getattr(context, 'results', []) if context else [],
                config={}
            )
            
            # Execute all analysis plugins
            results = await self.execute_plugins_by_type(
                plugin_type=PluginType.ANALYSIS,
                context=plugin_context,
                parallel=True
            )
            
            # Format results into a dictionary
            plugin_results = {}
            for result in results:
                plugin_results[result.plugin_name] = {
                    "success": result.success,
                    "data": result.result_data,
                    "error": result.error_message,
                    "execution_time_ms": result.execution_time_ms
                }
            
            logger.info(f"Processed message through {len(results)} plugins")
            return plugin_results
            
        except Exception as e:
            logger.error(f"Plugin message processing failed: {e}")
            return {}

    async def shutdown(self):
        """Shutdown plugin manager and cleanup all plugins."""
        logger.info("Shutting down plugin manager...")
        
        cleanup_tasks = []
        for plugin_name, plugin in self._plugins.items():
            if plugin.instance:
                cleanup_tasks.append(plugin.instance.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self._plugins.clear()
        self._plugin_dependencies.clear()
        
        for hook_list in self._execution_hooks.values():
            hook_list.clear()
        
        logger.info("Plugin manager shutdown complete")


# Global plugin manager instance
plugin_manager = PluginManager()


async def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance.
    
    Returns:
        Global PluginManager instance
    """
    return plugin_manager