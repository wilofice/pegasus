"""Plugin execution tasks for Celery workers."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from workers.celery_app import app
from workers.base_task import BaseTask
from models.job import JobType
from services.plugin_manager import plugin_manager, PluginContext, PluginType

logger = logging.getLogger(__name__)


@app.task(base=BaseTask, bind=True)
def execute_plugins_for_transcript(
    self,
    audio_id: str,
    plugin_types: List[str] = None,
    job_id: str = None
) -> Dict[str, Any]:
    """Execute plugins for a processed transcript.
    
    Args:
        audio_id: UUID of the audio file
        plugin_types: List of plugin types to execute (optional)
        job_id: UUID of the associated job
        
    Returns:
        Dict with plugin execution results
    """
    import asyncio
    
    async def _execute_plugins_async():
        try:
            # Validate inputs
            if not audio_id:
                raise ValueError("audio_id is required")
            
            audio_uuid = UUID(audio_id)
            self._job_id = UUID(job_id) if job_id else None
            
            logger.info(f"Starting plugin execution for audio {audio_id}")
            
            # Load audio file and transcript
            self.log_progress(1, 5, "Loading audio file and transcript")
            
            from core.database import get_db_session
            from models.audio_file import AudioFile
            
            db_session = next(get_db_session())
            try:
                audio_file = db_session.query(AudioFile).filter(AudioFile.id == audio_uuid).first()
                
                if not audio_file:
                    raise ValueError(f"Audio file {audio_id} not found")
                
                if not audio_file.improved_transcript:
                    raise ValueError(f"No improved transcript found for audio file {audio_id}")
                
                # Create plugin context
                self.log_progress(2, 5, "Creating plugin context")
                
                # Get chunks if available from ChromaDB
                chunks = []
                try:
                    chunk_results = await self.chromadb_client.query(
                        query_texts=[audio_file.improved_transcript[:100]],  # Use beginning as query
                        n_results=50,
                        where={"audio_id": audio_id}
                    )
                    
                    if chunk_results and chunk_results['documents']:
                        documents = chunk_results['documents'][0]
                        metadatas = chunk_results['metadatas'][0] if chunk_results['metadatas'] else []
                        ids = chunk_results['ids'][0] if chunk_results['ids'] else []
                        
                        for i, doc in enumerate(documents):
                            chunk_metadata = metadatas[i] if i < len(metadatas) else {}
                            chunk_id = ids[i] if i < len(ids) else f"chunk_{i}"
                            
                            chunks.append({
                                "id": chunk_id,
                                "text": doc,
                                "metadata": chunk_metadata
                            })
                
                except Exception as e:
                    logger.warning(f"Could not load chunks from ChromaDB: {e}")
                
                # Get entities if available from Neo4j
                entities = []
                try:
                    entity_query = """
                    MATCH (c:AudioChunk {audio_id: $audio_id})-[:CONTAINS_ENTITY]->(e:Entity)
                    RETURN DISTINCT e.text as text, e.type as type, e.normalized_text as normalized_text
                    LIMIT 100
                    """
                    
                    entity_results = await self.neo4j_client.execute_read_query(
                        entity_query,
                        {"audio_id": audio_id}
                    )
                    
                    for record in entity_results or []:
                        entities.append({
                            "text": record.get("text"),
                            "type": record.get("type"),
                            "normalized_text": record.get("normalized_text")
                        })
                
                except Exception as e:
                    logger.warning(f"Could not load entities from Neo4j: {e}")
                
                # Create plugin context
                context = PluginContext(
                    audio_id=audio_id,
                    user_id=str(audio_file.user_id),
                    transcript=audio_file.improved_transcript,
                    metadata={
                        "original_transcript": audio_file.original_transcript,
                        "language": audio_file.language,
                        "tags": audio_file.tag,
                        "category": audio_file.category,
                        "upload_timestamp": audio_file.upload_timestamp.isoformat() if audio_file.upload_timestamp else None,
                        "file_name": audio_file.file_name,
                        "vector_indexed": audio_file.vector_indexed,
                        "graph_indexed": audio_file.graph_indexed,
                        "entities_extracted": audio_file.entities_extracted
                    },
                    chunks=chunks,
                    entities=entities
                )
                
                # Execute plugins by type
                self.log_progress(3, 5, "Executing plugins")
                
                plugin_results = {}
                
                if plugin_types:
                    # Execute specific plugin types
                    for plugin_type_str in plugin_types:
                        try:
                            plugin_type = PluginType(plugin_type_str)
                            results = await plugin_manager.execute_plugins_by_type(
                                plugin_type, context, parallel=True
                            )
                            plugin_results[plugin_type_str] = [
                                {
                                    "plugin_name": r.plugin_name,
                                    "success": r.success,
                                    "result_data": r.result_data,
                                    "error_message": r.error_message,
                                    "execution_time_ms": r.execution_time_ms,
                                    "metadata": r.metadata
                                }
                                for r in results
                            ]
                        except ValueError as e:
                            logger.warning(f"Invalid plugin type {plugin_type_str}: {e}")
                            plugin_results[plugin_type_str] = []
                else:
                    # Execute all plugin types
                    for plugin_type in PluginType:
                        results = await plugin_manager.execute_plugins_by_type(
                            plugin_type, context, parallel=True
                        )
                        if results:  # Only include types that have results
                            plugin_results[plugin_type.value] = [
                                {
                                    "plugin_name": r.plugin_name,
                                    "success": r.success,
                                    "result_data": r.result_data,
                                    "error_message": r.error_message,
                                    "execution_time_ms": r.execution_time_ms,
                                    "metadata": r.metadata
                                }
                                for r in results
                            ]
                
                # Store plugin results in database (optional)
                self.log_progress(4, 5, "Storing plugin results")
                
                # You could store results in a dedicated table or add to audio_file metadata
                # For now, we'll just log the results
                total_plugins = sum(len(results) for results in plugin_results.values())
                successful_plugins = sum(
                    len([r for r in results if r["success"]]) 
                    for results in plugin_results.values()
                )
                
                logger.info(f"Plugin execution completed: {successful_plugins}/{total_plugins} successful")
                
                # Update completion status
                self.log_progress(5, 5, "Plugin execution completed")
                
                result = {
                    "audio_id": audio_id,
                    "plugin_results": plugin_results,
                    "total_plugins_executed": total_plugins,
                    "successful_plugins": successful_plugins,
                    "chunks_available": len(chunks),
                    "entities_available": len(entities),
                    "processing_completed_at": asyncio.get_event_loop().time()
                }
                
                logger.info(f"Successfully executed plugins for audio {audio_id}")
                return result
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Failed to execute plugins for audio {audio_id}: {e}")
            raise
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_plugins_async())


@app.task(base=BaseTask, bind=True)
def execute_single_plugin(
    self,
    plugin_name: str,
    audio_id: str,
    plugin_config: Dict[str, Any] = None,
    job_id: str = None
) -> Dict[str, Any]:
    """Execute a single plugin for a transcript.
    
    Args:
        plugin_name: Name of the plugin to execute
        audio_id: UUID of the audio file
        plugin_config: Optional plugin-specific configuration
        job_id: UUID of the associated job
        
    Returns:
        Dict with plugin execution result
    """
    import asyncio
    
    async def _execute_single_plugin_async():
        try:
            # Validate inputs
            if not plugin_name or not audio_id:
                raise ValueError("plugin_name and audio_id are required")
            
            audio_uuid = UUID(audio_id)
            self._job_id = UUID(job_id) if job_id else None
            
            logger.info(f"Executing plugin {plugin_name} for audio {audio_id}")
            
            # Load audio file and transcript
            self.log_progress(1, 3, f"Loading data for plugin {plugin_name}")
            
            from core.database import get_db_session
            from models.audio_file import AudioFile
            
            db_session = next(get_db_session())
            try:
                audio_file = db_session.query(AudioFile).filter(AudioFile.id == audio_uuid).first()
                
                if not audio_file:
                    raise ValueError(f"Audio file {audio_id} not found")
                
                if not audio_file.improved_transcript:
                    raise ValueError(f"No improved transcript found for audio file {audio_id}")
                
                # Create simplified context for single plugin
                context = PluginContext(
                    audio_id=audio_id,
                    user_id=str(audio_file.user_id),
                    transcript=audio_file.improved_transcript,
                    metadata={
                        "language": audio_file.language,
                        "tags": audio_file.tag,
                        "category": audio_file.category,
                        "file_name": audio_file.file_name
                    },
                    config=plugin_config or {}
                )
                
                # Execute single plugin
                self.log_progress(2, 3, f"Executing plugin {plugin_name}")
                
                result = await plugin_manager.execute_plugin(plugin_name, context)
                
                # Prepare response
                self.log_progress(3, 3, "Plugin execution completed")
                
                response = {
                    "audio_id": audio_id,
                    "plugin_name": plugin_name,
                    "success": result.success,
                    "result_data": result.result_data,
                    "error_message": result.error_message,
                    "execution_time_ms": result.execution_time_ms,
                    "metadata": result.metadata,
                    "processing_completed_at": asyncio.get_event_loop().time()
                }
                
                logger.info(f"Plugin {plugin_name} execution completed: success={result.success}")
                return response
                
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Failed to execute plugin {plugin_name} for audio {audio_id}: {e}")
            raise
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_execute_single_plugin_async())


@app.task(base=BaseTask, bind=True)
def reload_plugin(self, plugin_name: str, job_id: str = None) -> Dict[str, Any]:
    """Reload a plugin configuration.
    
    Args:
        plugin_name: Name of the plugin to reload
        job_id: UUID of the associated job
        
    Returns:
        Dict with reload result
    """
    import asyncio
    
    async def _reload_plugin_async():
        try:
            if not plugin_name:
                raise ValueError("plugin_name is required")
            
            self._job_id = UUID(job_id) if job_id else None
            
            logger.info(f"Reloading plugin {plugin_name}")
            
            self.log_progress(1, 2, f"Reloading plugin {plugin_name}")
            
            success = await plugin_manager.reload_plugin(plugin_name)
            
            self.log_progress(2, 2, "Plugin reload completed")
            
            result = {
                "plugin_name": plugin_name,
                "reload_success": success,
                "completed_at": asyncio.get_event_loop().time()
            }
            
            if success:
                logger.info(f"Successfully reloaded plugin {plugin_name}")
            else:
                logger.error(f"Failed to reload plugin {plugin_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {e}")
            raise
    
    # Run the async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_reload_plugin_async())


@app.task(base=BaseTask, bind=True)
def get_plugin_status(self, job_id: str = None) -> Dict[str, Any]:
    """Get status of all registered plugins.
    
    Args:
        job_id: UUID of the associated job
        
    Returns:
        Dict with plugin status information
    """
    try:
        self._job_id = UUID(job_id) if job_id else None
        
        logger.info("Getting plugin status")
        
        self.log_progress(1, 1, "Retrieving plugin status")
        
        # Get all plugins information
        plugins = plugin_manager.list_plugins()
        
        # Organize by type and status
        by_type = {}
        by_status = {}
        
        for plugin in plugins:
            plugin_type = plugin['type']
            status = plugin['status']
            
            if plugin_type not in by_type:
                by_type[plugin_type] = []
            by_type[plugin_type].append(plugin)
            
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(plugin)
        
        result = {
            "total_plugins": len(plugins),
            "plugins": plugins,
            "by_type": by_type,
            "by_status": by_status,
            "plugin_types_available": list(by_type.keys()),
            "status_summary": {status: len(plugins) for status, plugins in by_status.items()},
            "retrieved_at": asyncio.get_event_loop().time()
        }
        
        logger.info(f"Retrieved status for {len(plugins)} plugins")
        return result
        
    except Exception as e:
        logger.error(f"Error getting plugin status: {e}")
        raise