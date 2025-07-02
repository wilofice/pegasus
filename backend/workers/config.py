"""Celery configuration for Pegasus Brain."""
import os
from kombu import Queue, Exchange
from celery import Celery

from core.config import settings

# Celery configuration
broker_url = getattr(settings, 'celery_broker_url', 'redis://localhost:6379/0')
result_backend = getattr(settings, 'celery_result_backend', 'db+postgresql://pegasus:pegasus@localhost/pegasus_db')

# Task configuration
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker configuration
worker_prefetch_multiplier = 1
task_acks_late = True
worker_max_tasks_per_child = 1000

# Task execution
task_soft_time_limit = getattr(settings, 'task_timeout', 300)  # 5 minutes soft limit
task_time_limit = task_soft_time_limit + 60  # 1 minute hard limit buffer

# Error handling
task_reject_on_worker_lost = True
task_ignore_result = False

# Retry configuration
task_default_retry_delay = 60  # 1 minute
task_max_retry_delay = 600  # 10 minutes
task_default_max_retries = 3

# Queue configuration
task_default_queue = 'default'
task_routes = {
    'workers.tasks.transcript_processor.*': {'queue': 'transcript_processing'},
    'workers.tasks.vector_indexer.*': {'queue': 'vector_indexing'},
    'workers.tasks.graph_builder.*': {'queue': 'graph_building'},
    'workers.tasks.entity_extractor.*': {'queue': 'entity_extraction'},
    'workers.tasks.plugin_executor.*': {'queue': 'plugin_execution'},
}

# Define queues with priorities
task_queues = (
    Queue('default', Exchange('default'), routing_key='default', priority=0),
    Queue('transcript_processing', Exchange('transcript'), routing_key='transcript.processing', priority=5),
    Queue('vector_indexing', Exchange('indexing'), routing_key='indexing.vector', priority=3),
    Queue('graph_building', Exchange('indexing'), routing_key='indexing.graph', priority=3),
    Queue('entity_extraction', Exchange('nlp'), routing_key='nlp.entities', priority=4),
    Queue('plugin_execution', Exchange('plugins'), routing_key='plugin.execute', priority=2),
)

# Monitoring
worker_send_task_events = True
task_send_sent_event = True

# Security
worker_hijack_root_logger = False
worker_log_color = False

# Beat schedule (for periodic tasks)
beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'workers.tasks.maintenance.cleanup_old_jobs',
        'schedule': 86400.0,  # Run daily
        'options': {'queue': 'default'}
    },
    'health-check-services': {
        'task': 'workers.tasks.maintenance.health_check_services',
        'schedule': 300.0,  # Run every 5 minutes
        'options': {'queue': 'default'}
    },
}