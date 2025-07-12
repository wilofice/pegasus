#!/usr/bin/env python3
"""Start Celery worker for Pegasus Brain processing."""
import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the Celery worker."""
    try:
        from workers.celery_app import app
        
        logger.info("Starting Pegasus Brain Celery worker...")
        
        # Configure worker arguments
        worker_args = [
            'worker',
            '--loglevel=info',
            '--concurrency=2',  # Adjust based on your system
            '--prefetch-multiplier=1',
            '--without-gossip',
            '--without-mingle',
            '--without-heartbeat',
            '--pool=solo',
        ]
        
        # Add queue specification
        queues = [
            'default',
            'transcript_processing', 
            'vector_indexing',
            'graph_building',
            'entity_extraction',
            'plugin_execution'
        ]
        worker_args.extend(['--queues', ','.join(queues)])
        
        # Start the worker
        app.worker_main(worker_args)
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed to start: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()