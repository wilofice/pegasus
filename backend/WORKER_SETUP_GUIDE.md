# Pegasus Backend Worker Setup Guide

This guide explains how to run the complete Pegasus backend system with both audio processing stages.

## Overview

The Pegasus backend uses a two-stage processing pipeline:

1. **Stage 1: Audio Processing** (FastAPI BackgroundTask)
   - Transcribes audio using Whisper/Deepgram
   - Improves transcript using Ollama LLM
   - Runs within the FastAPI process

2. **Stage 2: Brain Indexing** (Celery Task)
   - Extracts entities from transcript
   - Creates embeddings and stores in ChromaDB
   - Builds knowledge graph in Neo4j
   - Runs in separate Celery worker process

## Prerequisites

1. **Services Running:**
   - PostgreSQL (for application data)
   - Redis (for Celery message broker)
   - Neo4j (for knowledge graph)
   - ChromaDB (for vector embeddings)
   - Ollama (for transcript improvement)

2. **Environment Configuration:**
   - Ensure `.env` file is properly configured
   - All API keys and connection strings set

## Starting the System

### 1. Start Required Services

```bash
# Start PostgreSQL (if using Docker)
docker run -d --name pegasus-postgres \
  -e POSTGRES_USER=pegasus_user \
  -e POSTGRES_PASSWORD=pegasus_password \
  -e POSTGRES_DB=pegasus_db \
  -p 5432:5432 postgres:14

# Start Redis
docker run -d --name pegasus-redis -p 6379:6379 redis:7

# Start Neo4j
docker run -d --name pegasus-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/pegasus_neo4j_password \
  neo4j:5-community

# Start ChromaDB
docker run -d --name pegasus-chromadb \
  -p 8001:8000 \
  chromadb/chroma

# Start Ollama (native installation)
ollama serve
```

### 2. Initialize Database

```bash
cd backend
python scripts/init_db.py
```

### 3. Start the FastAPI Server

```bash
# Terminal 1
cd backend
source venv/bin/activate
python main.py
```

The API will be available at `http://localhost:8000`

### 4. Start the Celery Worker

```bash
# Terminal 2
cd backend
source venv/bin/activate
python start_worker.py
```

Or manually with Celery:

```bash
celery -A workers.celery_app worker --loglevel=info
```

### 5. (Optional) Start Celery Flower for Monitoring

```bash
# Terminal 3
cd backend
source venv/bin/activate
celery -A workers.celery_app flower
```

Access Flower at `http://localhost:5555` to monitor tasks.

## Processing Flow

1. **Upload Audio File**
   ```bash
   curl -X POST http://localhost:8000/api/audio/upload \
     -F "file=@recording.m4a" \
     -F "user_id=user123" \
     -F "language=en"
   ```

2. **Stage 1 Processing** (Automatic)
   - Status changes: `uploaded` → `transcribing` → `improving` → `completed`
   - Check status: `GET /api/audio/{audio_id}`

3. **Stage 2 Processing** (Automatic after Stage 1)
   - Celery task triggered automatically when Stage 1 completes
   - Updates indexing flags: `vector_indexed`, `graph_indexed`, `entities_extracted`
   - Check indexing status: `GET /api/audio/{audio_id}/indexing-status`

## Monitoring

### Check Audio Processing Status

```bash
# Get audio file details
curl http://localhost:8000/api/audio/{audio_id}

# Get transcript
curl http://localhost:8000/api/audio/{audio_id}/transcript

# Get indexing status
curl http://localhost:8000/api/audio/{audio_id}/indexing-status
```

### Check Worker Health

```bash
# Check if Celery worker is running
celery -A workers.celery_app inspect active

# Check registered tasks
celery -A workers.celery_app inspect registered

# Check task stats
celery -A workers.celery_app inspect stats
```

## Troubleshooting

### Worker Not Processing Tasks

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check worker logs for errors
3. Ensure worker is subscribed to correct queues:
   ```bash
   celery -A workers.celery_app inspect active_queues
   ```

### Tasks Failing

1. Check audio file has improved transcript:
   ```sql
   SELECT id, processing_status, improved_transcript IS NOT NULL 
   FROM audio_files WHERE id = 'your-audio-id';
   ```

2. Check job status:
   ```sql
   SELECT * FROM processing_jobs 
   WHERE parameters->>'audio_id' = 'your-audio-id';
   ```

3. Check Celery task result:
   ```bash
   celery -A workers.celery_app result <task-id>
   ```

### Indexing Not Working

1. Verify Neo4j is accessible:
   ```bash
   curl http://localhost:7474
   ```

2. Verify ChromaDB is accessible:
   ```bash
   curl http://localhost:8001/api/v1/heartbeat
   ```

## Configuration

### Celery Worker Settings

Edit `start_worker.py` to adjust:
- `--concurrency`: Number of worker processes
- `--queues`: Which queues to process
- `--prefetch-multiplier`: Tasks to prefetch per worker

### Processing Timeouts

In `.env`:
```env
TASK_TIMEOUT=300  # 5 minutes per task
CELERY_TASK_TIME_LIMIT=600  # Hard limit
CELERY_TASK_SOFT_TIME_LIMIT=300  # Soft limit
```

## Production Considerations

1. **Use a Process Manager**
   - systemd services for Linux
   - supervisord for process management
   - Docker Compose for containerized deployment

2. **Scale Workers**
   ```bash
   # Run multiple workers
   celery -A workers.celery_app worker --concurrency=4 -n worker1@%h
   celery -A workers.celery_app worker --concurrency=4 -n worker2@%h
   ```

3. **Monitor Resources**
   - Redis memory usage
   - PostgreSQL connections
   - Neo4j heap size
   - Worker CPU/memory

4. **Setup Logging**
   - Configure centralized logging
   - Set appropriate log levels
   - Rotate logs regularly