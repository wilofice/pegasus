#!/bin/bash

# Pegasus Brain Services Health Check Script

set -e

echo "🔍 Checking Pegasus Brain services health..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local health_check=$2
    local description=$3
    
    echo -n "Checking $description... "
    
    if eval "$health_check" &>/dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local health_check=$2
    local description=$3
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $description to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$health_check" &>/dev/null; then
            echo -e "${GREEN}✓ $description is ready!${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}✗ $description failed to start within timeout${NC}"
    return 1
}

# Check if Docker is running
echo "🐳 Checking Docker..."
if ! docker info &>/dev/null; then
    echo -e "${RED}✗ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Start services if not running
echo "🚀 Starting Pegasus Brain services..."
docker compose up -d

# Wait for services to be ready
echo
echo "⏳ Waiting for services to initialize..."

# PostgreSQL
wait_for_service "postgres" \
    "docker compose exec -T postgres pg_isready -U \${POSTGRES_USER:-pegasus_user}" \
    "PostgreSQL"

# Redis
wait_for_service "redis" \
    "docker compose exec -T redis redis-cli ping | grep PONG" \
    "Redis"

# Neo4j
wait_for_service "neo4j" \
    "curl -f http://localhost:7474 -o /dev/null -s" \
    "Neo4j"

# ChromaDB
wait_for_service "chromadb" \
    "curl -f http://localhost:8001/api/v1/heartbeat -o /dev/null -s" \
    "ChromaDB"

# Ollama
wait_for_service "ollama" \
    "curl -f http://localhost:11434/api/tags -o /dev/null -s" \
    "Ollama"

echo
echo "🔍 Final health check..."

# Run detailed health checks
health_status=0

check_service "postgres" \
    "docker compose exec -T postgres pg_isready -U \${POSTGRES_USER:-pegasus_user}" \
    "PostgreSQL Database" || health_status=1

check_service "redis" \
    "docker compose exec -T redis redis-cli ping | grep PONG" \
    "Redis Cache" || health_status=1

check_service "neo4j" \
    "curl -f http://localhost:7474 -o /dev/null -s" \
    "Neo4j Graph Database" || health_status=1

check_service "chromadb" \
    "curl -f http://localhost:8001/api/v1/heartbeat -o /dev/null -s" \
    "ChromaDB Vector Database" || health_status=1

check_service "ollama" \
    "curl -f http://localhost:11434/api/tags -o /dev/null -s" \
    "Ollama LLM Service" || health_status=1

echo
if [ $health_status -eq 0 ]; then
    echo -e "${GREEN}🎉 All Pegasus Brain services are healthy and ready!${NC}"
    echo
    echo "📊 Service Endpoints:"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo "  • Neo4j Browser: http://localhost:7474"
    echo "  • ChromaDB API: http://localhost:8001"
    echo "  • Ollama API: http://localhost:11434"
    echo
    echo "🔐 Default Credentials:"
    echo "  • Neo4j: neo4j / pegasus_neo4j_password"
    echo "  • PostgreSQL: pegasus_user / pegasus_password"
else
    echo -e "${RED}❌ Some services are not healthy. Check docker compose logs for details.${NC}"
    echo "Run 'docker compose logs [service_name]' to debug issues."
    exit 1
fi