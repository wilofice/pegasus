"""Celery application instance for Pegasus Brain."""
import logging
from celery import Celery
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun

from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery('pegasus_brain')

# Load configuration
app.config_from_object('workers.config')

# Auto-discover tasks
app.autodiscover_tasks([
    'workers.tasks',
    'workers.tasks.transcription_tasks',
    'workers.tasks.conversation_processing_tasks',
    'workers.tasks.transcript_processor',
    'workers.tasks.vector_indexer', 
    'workers.tasks.graph_builder',
    'workers.tasks.entity_extractor',
    'workers.tasks.plugin_executor',
    'workers.tasks.maintenance'
])


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info(f"Celery worker {sender.hostname} is ready")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(f"Celery worker {sender.hostname} is shutting down")


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal."""
    logger.info(f"Starting task {task.name} [{task_id}]")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task postrun signal."""
    logger.info(f"Finished task {task.name} [{task_id}] with state: {state}")


# Health check task
@app.task(bind=True)
def health_check(self):
    """Basic health check task."""
    try:
        from services.neo4j_client import get_neo4j_client
        from services.vector_db_client import get_chromadb_client
        
        # Test database connections
        neo4j_client = get_neo4j_client()
        chromadb_client = get_chromadb_client()
        
        return {
            "status": "healthy",
            "worker_id": self.request.id,
            "neo4j": "connected",
            "chromadb": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "error": str(e)
        }


if __name__ == '__main__':
    app.start()