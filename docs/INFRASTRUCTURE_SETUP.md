# Pegasus Brain Infrastructure Setup

This document describes how to set up the Pegasus Brain infrastructure using Docker Compose.

## Prerequisites

- Docker 20.10+ with Docker Compose v2
- 8GB RAM minimum
- 10GB free disk space
- Ports 5432, 6379, 7474, 7687, 8001, 11434 available

## Quick Start

1. **Copy environment configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Start all services:**
   ```bash
   docker compose up -d
   ```

3. **Verify health:**
   ```bash
   ./scripts/health_check.sh
   ```

## Services Overview

| Service | Description | Port | Health Check URL |
|---------|-------------|------|------------------|
| PostgreSQL | Main database | 5432 | `pg_isready` |
| Redis | Job queue broker | 6379 | `redis-cli ping` |
| Neo4j | Graph database | 7474, 7687 | http://localhost:7474 |
| ChromaDB | Vector database | 8001 | http://localhost:8001/api/v1/heartbeat |
| Ollama | Local LLM | 11434 | http://localhost:11434/api/tags |

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database connections
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
CHROMADB_HOST=localhost
CHROMADB_PORT=8001

# Authentication
NEO4J_USER=neo4j
NEO4J_PASSWORD=pegasus_neo4j_password
POSTGRES_USER=pegasus_user
POSTGRES_PASSWORD=pegasus_password
```

### Service-Specific Configuration

#### Neo4j
- Default credentials: `neo4j` / `pegasus_neo4j_password`
- Browser interface: http://localhost:7474
- APOC plugin pre-installed for advanced graph operations
- Memory: 512M initial, 1G max heap

#### ChromaDB
- HTTP API endpoint: http://localhost:8001
- Persistent storage enabled
- Anonymous telemetry disabled
- Data persisted to Docker volume

#### Redis
- Memory limit: 512MB
- Eviction policy: allkeys-lru
- Persistence: appendonly enabled
- Data persisted to Docker volume

## Manual Testing

### Test PostgreSQL Connection
```bash
docker compose exec postgres psql -U pegasus_user -d pegasus_db -c "SELECT version();"
```

### Test Redis Connection
```bash
docker compose exec redis redis-cli ping
# Expected: PONG
```

### Test Neo4j Connection
```bash
curl -u neo4j:pegasus_neo4j_password -H "Content-Type: application/json" \
  -d '{"statements":[{"statement":"RETURN 1 as test"}]}' \
  http://localhost:7474/db/data/transaction/commit
```

### Test ChromaDB Connection
```bash
curl http://localhost:8001/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": [timestamp]}
```

### Test Ollama Connection
```bash
curl http://localhost:11434/api/tags
# Expected: {"models": [...]}
```

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Check if ports are already in use: `netstat -tulpn | grep [PORT]`
   - Modify port mappings in docker-compose.yml if needed

2. **Memory issues:**
   - Ensure Docker has sufficient memory allocated (8GB+)
   - Reduce service memory limits if needed

3. **Permission issues:**
   - Ensure Docker daemon is running with proper permissions
   - Check volume mount permissions

4. **Service startup order:**
   - Services have health checks and depend_on configurations
   - Allow 30-60 seconds for all services to become healthy

### Debug Commands

```bash
# Check service status
docker compose ps

# View logs for specific service
docker compose logs [service_name]

# Restart specific service
docker compose restart [service_name]

# Stop all services
docker compose down

# Stop and remove volumes (data loss!)
docker compose down -v
```

## Data Persistence

All services use Docker volumes for data persistence:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis persistence files
- `neo4j_data`: Neo4j graph database
- `chromadb_data`: ChromaDB vector storage
- `ollama_data`: Ollama models and cache

To backup data:
```bash
docker compose exec postgres pg_dump -U pegasus_user pegasus_db > backup.sql
```

To restore data:
```bash
docker compose exec -T postgres psql -U pegasus_user pegasus_db < backup.sql
```

## Production Considerations

For production deployment:

1. **Security:**
   - Change default passwords
   - Use environment-specific secrets
   - Enable TLS/SSL for external connections
   - Configure firewall rules

2. **Performance:**
   - Tune database configurations
   - Monitor resource usage
   - Set up proper logging
   - Configure backup strategies

3. **Monitoring:**
   - Add health check endpoints to load balancers
   - Set up metrics collection (Prometheus/Grafana)
   - Configure alerting for service failures