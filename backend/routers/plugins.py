"""Plugin management API endpoints."""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from services.plugin_manager import plugin_manager, PluginType, PluginStatus
from workers.tasks.plugin_executor import (
    execute_plugins_for_transcript,
    execute_single_plugin,
    reload_plugin,
    get_plugin_status
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginExecutionRequest(BaseModel):
    """Request model for plugin execution."""
    audio_id: str = Field(..., description="Audio file ID")
    plugin_types: Optional[List[str]] = Field(default=None, description="Plugin types to execute")
    plugin_config: Optional[Dict[str, Any]] = Field(default=None, description="Plugin configuration")


class SinglePluginExecutionRequest(BaseModel):
    """Request model for single plugin execution."""
    audio_id: str = Field(..., description="Audio file ID")
    plugin_name: str = Field(..., description="Plugin name to execute")
    plugin_config: Optional[Dict[str, Any]] = Field(default=None, description="Plugin configuration")


class PluginInfo(BaseModel):
    """Plugin information model."""
    name: str
    version: str
    description: str
    author: str
    type: str
    status: str
    dependencies: List[str]
    tags: List[str]
    config: Dict[str, Any]
    last_error: Optional[str]
    created_at: str
    updated_at: str


class PluginExecutionResponse(BaseModel):
    """Response model for plugin execution."""
    task_id: str
    message: str
    audio_id: str
    estimated_completion_time: Optional[str] = None


@router.get("/", response_model=List[PluginInfo])
async def list_plugins(
    plugin_type: Optional[str] = None,
    status: Optional[str] = None
):
    """List all registered plugins with optional filtering.
    
    **Filters:**
    - `plugin_type`: Filter by plugin type (analysis, processing, notification, etc.)
    - `status`: Filter by plugin status (enabled, disabled, error, loading)
    
    **Returns:**
    List of plugin information including metadata, status, and configuration.
    """
    try:
        # Validate filters
        filter_type = None
        filter_status = None
        
        if plugin_type:
            try:
                filter_type = PluginType(plugin_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid plugin type: {plugin_type}. Valid types: {[t.value for t in PluginType]}"
                )
        
        if status:
            try:
                filter_status = PluginStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid plugin status: {status}. Valid statuses: {[s.value for s in PluginStatus]}"
                )
        
        # Get plugins
        plugins = plugin_manager.list_plugins(filter_type, filter_status)
        
        return [PluginInfo(**plugin) for plugin in plugins]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list plugins: {str(e)}"
        )


@router.get("/{plugin_name}", response_model=PluginInfo)
async def get_plugin_info(plugin_name: str):
    """Get detailed information about a specific plugin.
    
    **Parameters:**
    - `plugin_name`: Name of the plugin to retrieve information for
    
    **Returns:**
    Detailed plugin information including metadata, configuration, and status.
    """
    try:
        plugin_info = plugin_manager.get_plugin_info(plugin_name)
        
        if not plugin_info:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{plugin_name}' not found"
            )
        
        return PluginInfo(**plugin_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin info for {plugin_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plugin info: {str(e)}"
        )


@router.post("/execute", response_model=PluginExecutionResponse)
async def execute_plugins(
    request: PluginExecutionRequest,
    background_tasks: BackgroundTasks
):
    """Execute plugins for a transcript.
    
    This endpoint queues plugin execution for a processed transcript.
    The execution happens asynchronously in the background.
    
    **Plugin Types:**
    - `analysis`: Text analysis plugins (sentiment, topics, keywords)
    - `processing`: Text processing plugins (summarization, enhancement)
    - `notification`: Notification plugins (email, slack, webhooks)
    - `export`: Export plugins (PDF, Word, databases)
    - `integration`: Integration plugins (CRM, project management)
    
    **Use Cases:**
    - Analyze sentiment and topics of meeting transcripts
    - Generate summaries and action items
    - Send notifications to team members
    - Export transcripts to external systems
    """
    try:
        # Validate plugin types if provided
        if request.plugin_types:
            for plugin_type in request.plugin_types:
                try:
                    PluginType(plugin_type)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid plugin type: {plugin_type}. Valid types: {[t.value for t in PluginType]}"
                    )
        
        # Queue plugin execution task
        task = execute_plugins_for_transcript.delay(
            audio_id=request.audio_id,
            plugin_types=request.plugin_types
        )
        
        return PluginExecutionResponse(
            task_id=task.id,
            message="Plugin execution queued successfully",
            audio_id=request.audio_id,
            estimated_completion_time="1-5 minutes"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing plugins: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute plugins: {str(e)}"
        )


@router.post("/execute-single", response_model=PluginExecutionResponse)
async def execute_single_plugin_endpoint(
    request: SinglePluginExecutionRequest,
    background_tasks: BackgroundTasks
):
    """Execute a single plugin for a transcript.
    
    This endpoint allows you to execute a specific plugin with custom
    configuration for a processed transcript.
    
    **Use Cases:**
    - Test a specific plugin with custom parameters
    - Re-run a failed plugin with different configuration
    - Execute plugins on-demand for specific analysis
    """
    try:
        # Check if plugin exists
        plugin_info = plugin_manager.get_plugin_info(request.plugin_name)
        if not plugin_info:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{request.plugin_name}' not found"
            )
        
        # Check if plugin is enabled
        if plugin_info['status'] != 'enabled':
            raise HTTPException(
                status_code=400,
                detail=f"Plugin '{request.plugin_name}' is not enabled (status: {plugin_info['status']})"
            )
        
        # Queue single plugin execution task
        task = execute_single_plugin.delay(
            plugin_name=request.plugin_name,
            audio_id=request.audio_id,
            plugin_config=request.plugin_config
        )
        
        return PluginExecutionResponse(
            task_id=task.id,
            message=f"Plugin '{request.plugin_name}' execution queued successfully",
            audio_id=request.audio_id,
            estimated_completion_time="30 seconds - 2 minutes"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing single plugin: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute plugin: {str(e)}"
        )


@router.post("/{plugin_name}/reload")
async def reload_plugin_endpoint(plugin_name: str, background_tasks: BackgroundTasks):
    """Reload a plugin configuration.
    
    This endpoint allows you to reload a plugin without restarting
    the entire system. Useful for applying configuration changes
    or recovering from plugin errors.
    
    **Parameters:**
    - `plugin_name`: Name of the plugin to reload
    
    **Use Cases:**
    - Apply configuration changes
    - Recover from plugin errors
    - Update plugin code (with hot-reloading support)
    """
    try:
        # Check if plugin exists
        plugin_info = plugin_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{plugin_name}' not found"
            )
        
        # Queue plugin reload task
        task = reload_plugin.delay(plugin_name=plugin_name)
        
        return {
            "task_id": task.id,
            "message": f"Plugin '{plugin_name}' reload queued successfully",
            "plugin_name": plugin_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reloading plugin {plugin_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload plugin: {str(e)}"
        )


@router.get("/status/overview")
async def get_plugins_status():
    """Get overview of all plugin statuses.
    
    **Returns:**
    Comprehensive overview of plugin system including:
    - Total plugin count
    - Plugins grouped by type and status
    - System health information
    - Available plugin types
    """
    try:
        # Queue status retrieval task and wait for result
        task = get_plugin_status.delay()
        result = task.get(timeout=30)  # Wait up to 30 seconds
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting plugin status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plugin status: {str(e)}"
        )


@router.get("/types/available")
async def get_available_plugin_types():
    """Get list of available plugin types.
    
    **Returns:**
    List of plugin types with descriptions and use cases.
    """
    return {
        "plugin_types": {
            "analysis": {
                "name": "Analysis",
                "description": "Plugins that analyze transcript content",
                "examples": ["sentiment analysis", "topic classification", "keyword extraction"],
                "use_cases": ["Understanding meeting sentiment", "Categorizing content", "Finding key topics"]
            },
            "processing": {
                "name": "Processing",
                "description": "Plugins that process and transform transcript content",
                "examples": ["summarization", "action item extraction", "language translation"],
                "use_cases": ["Creating meeting summaries", "Extracting tasks", "Multi-language support"]
            },
            "notification": {
                "name": "Notification",
                "description": "Plugins that send notifications based on transcript content",
                "examples": ["email alerts", "slack notifications", "webhook triggers"],
                "use_cases": ["Alerting team members", "Triggering workflows", "Real-time updates"]
            },
            "export": {
                "name": "Export",
                "description": "Plugins that export transcript data to external formats",
                "examples": ["PDF generation", "database insertion", "API publishing"],
                "use_cases": ["Creating reports", "Data archival", "System integration"]
            },
            "integration": {
                "name": "Integration",
                "description": "Plugins that integrate with external systems",
                "examples": ["CRM updates", "project management", "calendar scheduling"],
                "use_cases": ["Updating customer records", "Creating tasks", "Scheduling follow-ups"]
            }
        },
        "total_types": len(PluginType),
        "registration_info": "Plugins are automatically discovered and registered at startup"
    }


@router.get("/health")
async def plugins_health_check():
    """Health check for plugin system.
    
    **Returns:**
    Health status of the plugin system including:
    - Plugin manager status
    - Number of enabled/disabled plugins
    - Recent errors or issues
    """
    try:
        plugins = plugin_manager.list_plugins()
        
        status_counts = {}
        for plugin in plugins:
            status = plugin['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check for any plugins in error state
        error_plugins = [p for p in plugins if p['status'] == 'error']
        
        return {
            "status": "healthy" if not error_plugins else "degraded",
            "total_plugins": len(plugins),
            "status_breakdown": status_counts,
            "error_plugins": [
                {
                    "name": p['name'],
                    "error": p['last_error']
                }
                for p in error_plugins
            ],
            "plugin_manager": "operational",
            "checked_at": "now"
        }
        
    except Exception as e:
        logger.error(f"Plugin health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "plugin_manager": "error",
            "checked_at": "now"
        }