# Pegasus Brain Implementation Plan - Detailed Actionable Tasks

## Overview
This document provides a comprehensive, granular task breakdown for implementing the Pegasus Brain dual-memory system with plugin architecture. Each task is designed to be small, measurable, and independently testable.

---

# Phase 1: The Dual-Memory Foundation (Weeks 1-4)

## Infrastructure Setup

### Task 1: Create Docker Compose Configuration
**Description**: Set up Docker Compose file with all required services

**Input**:
- Existing backend requirements
- Service specifications (Redis, Neo4j, ChromaDB, PostgreSQL)

**Output**:
- `docker-compose.yml` file in project root
- `.env.example` with required environment variables
- Service health check endpoints

**Guidelines**:
```yaml
# docker-compose.yml structure
services:
  postgres:
    - Existing database with volume persistence
  redis:
    - Port 6379, persistence enabled
    - Memory limit: 512MB
  neo4j:
    - Port 7474 (HTTP), 7687 (Bolt)
    - Authentication enabled
    - Volume for data persistence
  chromadb:
    - Port 8001
    - Persistent volume
    - HTTP API enabled
```

**Test Scenario**:
```bash
# All services should start and be healthy
docker-compose up -d
docker-compose ps  # All services "healthy"
# Verify connectivity
curl http://localhost:7474  # Neo4j browser
curl http://localhost:8001  # ChromaDB API
redis-cli ping  # Should return PONG
```

---

### Task 2: Create Database Connection Services
**Description**: Create service classes for Neo4j and enhanced ChromaDB connections

**Input**:
- Connection parameters from environment
- Existing ChromaDB client pattern

**Output**:
- `backend/services/neo4j_client.py`
- Updated `backend/services/vector_db_client.py`
- Connection pooling implemented

**Guidelines**:
```python
# neo4j_client.py structure
class Neo4jClient:
    def __init__(self, uri, user, password)
    async def connect()
    async def close()
    async def execute_query(query, params)
    async def health_check()
```

**Test Scenario**:
```python
# Test connection and basic operations
client = Neo4jClient(...)
await client.connect()
result = await client.execute_query("RETURN 1 AS num")
assert result[0]['num'] == 1
```

---

### Task 3: Update PostgreSQL Schema for Job Tracking
**Description**: Create database migration for job queue tables

**Input**:
- Alembic migration structure
- Job tracking requirements

**Output**:
- New migration file: `004_add_job_queue_tables.py`
- Tables: `processing_jobs`, `job_status_history`

**Guidelines**:
```sql
-- processing_jobs table
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    input_data JSONB,
    result_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0
);
```

**Test Scenario**:
```bash
alembic upgrade head
# Verify tables exist
psql -c "\dt processing_jobs"
# Insert test job
INSERT INTO processing_jobs (id, job_type, status) VALUES (uuid_generate_v4(), 'transcript_processing', 'pending');
```

---

## Worker Development

### Task 4: Set Up Celery Application
**Description**: Configure Celery with Redis broker

**Input**:
- Redis connection parameters
- Worker configuration requirements

**Output**:
- `backend/workers/celery_app.py`
- `backend/workers/config.py`
- Worker startup script

**Guidelines**:
```python
# celery_app.py
from celery import Celery

app = Celery('pegasus_brain')
app.config_from_object('workers.config')

# Configuration includes:
# - Redis broker URL
# - Result backend (PostgreSQL)
# - Task serialization (JSON)
# - Error handling policies
```

**Test Scenario**:
```bash
# Start worker
celery -A workers.celery_app worker --loglevel=info
# Submit test task
from workers.celery_app import app
result = app.send_task('test.ping')
assert result.get(timeout=5) == 'pong'
```

---

### Task 5: Create Base Worker Task Class
**Description**: Implement base class for all worker tasks with error handling

**Input**:
- Celery task requirements
- Error handling patterns

**Output**:
- `backend/workers/base_task.py`
- Logging configuration
- Retry logic implementation

**Guidelines**:
```python
class BaseTask(celery.Task):
    def __init__(self):
        self.db = None
        self.neo4j = None
        self.chromadb = None
    
    def before_start(self, task_id, args, kwargs):
        # Initialize connections
        # Set up logging context
    
    def after_return(self, status, retval, task_id, args, kwargs):
        # Clean up connections
        # Log completion
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Log error details
        # Update job status in PostgreSQL
```

**Test Scenario**:
```python
# Test task inheritance and error handling
@app.task(base=BaseTask, bind=True)
def test_task(self):
    raise ValueError("Test error")

# Should log error and update job status
```

---

### Task 6: Implement Transcript Processing Worker
**Description**: Create worker task for processing audio transcripts

**Input**:
- Audio file ID
- Transcript text (original and improved)
- User metadata

**Output**:
- `backend/workers/tasks/transcript_processor.py`
- Processed chunks in both databases
- Job status updates

**Guidelines**:
```python
@app.task(base=BaseTask, bind=True)
def process_transcript(self, audio_id: str):
    # 1. Load transcript from PostgreSQL
    # 2. Update job status to 'processing'
    # 3. Chunk transcript
    # 4. Extract entities using NER
    # 5. Generate embeddings
    # 6. Store in ChromaDB
    # 7. Create graph nodes in Neo4j
    # 8. Update job status to 'completed'
```

**Test Scenario**:
```python
# Submit transcript processing job
result = process_transcript.delay(audio_id="test-audio-123")
# Verify data in both databases
# Check ChromaDB for chunks
# Check Neo4j for entity nodes
```

---

## NER Implementation

### Task 7: Create spaCy NER Service
**Description**: Implement Named Entity Recognition service

**Input**:
- Text chunks
- Language code
- Entity types to extract

**Output**:
- `backend/services/ner_service.py`
- Extracted entities with types and positions
- Confidence scores

**Guidelines**:
```python
class NERService:
    def __init__(self):
        self.models = {
            'en': spacy.load('en_core_web_sm'),
            'fr': spacy.load('fr_core_news_sm')
        }
    
    def extract_entities(self, text: str, language: str = 'en'):
        # Returns: [
        #   {"text": "John Doe", "type": "PERSON", "start": 0, "end": 8},
        #   {"text": "Paris", "type": "LOCATION", "start": 20, "end": 25}
        # ]
```

**Test Scenario**:
```python
ner = NERService()
entities = ner.extract_entities("John Doe visited Paris last week")
assert any(e['text'] == 'John Doe' and e['type'] == 'PERSON' for e in entities)
assert any(e['text'] == 'Paris' and e['type'] == 'LOCATION' for e in entities)
```

---

### Task 8: Create Custom Entity Rules
**Description**: Add domain-specific entity recognition rules

**Input**:
- Common patterns in user transcripts
- Domain-specific terms

**Output**:
- `backend/services/custom_entities.py`
- Pattern matchers for dates, tasks, projects
- Integration with spaCy pipeline

**Guidelines**:
```python
# Custom patterns for:
# - Task mentions: "I need to...", "Remember to..."
# - Project names: capitalized phrases
# - Deadlines: date patterns
# - Questions: "What about...?", "How do I...?"
```

**Test Scenario**:
```python
text = "I need to finish the Budget Report by Friday"
entities = extract_with_custom_rules(text)
assert any(e['type'] == 'TASK' for e in entities)
assert any(e['type'] == 'PROJECT' for e in entities)
assert any(e['type'] == 'DEADLINE' for e in entities)
```

---

## Document Processing

### Task 9: Implement Fixed-Size Chunking Service
**Description**: Create service for chunking documents with overlap

**Input**:
- Full text document
- Chunk size (tokens)
- Overlap size (tokens)

**Output**:
- `backend/services/chunking_service.py`
- List of chunks with metadata
- Chunk boundaries preservation

**Guidelines**:
```python
class ChunkingService:
    def __init__(self, chunk_size=500, overlap=50):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str) -> List[Chunk]:
        # Returns chunks with:
        # - text content
        # - start/end positions
        # - token count
        # - overlap indicators
```

**Test Scenario**:
```python
chunker = ChunkingService(chunk_size=100, overlap=20)
chunks = chunker.chunk_text("Long text..." * 50)
# Verify chunk sizes
# Verify overlap between consecutive chunks
# Ensure no content is lost
```

---

### Task 10: Create Embedding Generation Service
**Description**: Service for generating vector embeddings

**Input**:
- Text chunks
- Model selection
- Batch processing support

**Output**:
- `backend/services/embedding_service.py`
- Vector embeddings
- Embedding metadata

**Guidelines**:
```python
class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Batch processing for efficiency
        # Return normalized vectors
```

**Test Scenario**:
```python
embedder = EmbeddingService()
embeddings = await embedder.generate_embeddings(["Hello world", "Bonjour monde"])
assert len(embeddings) == 2
assert len(embeddings[0]) == 384  # Model dimension
```

---

## Dual-Database Integration

### Task 11: Create ChromaDB Collection Manager
**Description**: Enhanced ChromaDB management for audio transcripts

**Input**:
- Collection naming strategy
- Metadata schema
- Index configuration

**Output**:
- `backend/services/chromadb_manager.py`
- Collection initialization
- Metadata indexing

**Guidelines**:
```python
class ChromaDBManager:
    def ensure_collection(self, name: str = "audio_transcripts"):
        # Create or get collection
        # Set up metadata fields:
        # - audio_id, user_id, timestamp
        # - language, tags, chunk_index
        # - entity_count, sentiment_score
```

**Test Scenario**:
```python
manager = ChromaDBManager()
collection = manager.ensure_collection("test_transcripts")
# Add test documents
# Query with metadata filters
results = collection.query(
    query_texts=["test query"],
    where={"user_id": "test_user"}
)
```

---

### Task 12: Create Neo4j Schema Manager
**Description**: Initialize Neo4j graph schema and constraints

**Input**:
- Node types definition
- Relationship types
- Constraint requirements

**Output**:
- `backend/services/neo4j_schema.py`
- Schema initialization script
- Index creation

**Guidelines**:
```cypher
// Node types
CREATE CONSTRAINT person_name IF NOT EXISTS 
  FOR (p:Person) REQUIRE p.name IS UNIQUE;

// Relationship types
// (:AudioChunk)-[:MENTIONS]->(:Person)
// (:AudioChunk)-[:DISCUSSES]->(:Topic)
// (:Person)-[:RELATED_TO]->(:Project)
```

**Test Scenario**:
```python
schema_manager = Neo4jSchemaManager()
await schema_manager.initialize()
# Verify constraints exist
# Test node creation with constraints
```

---

### Task 13: Implement Graph Node Creation Service
**Description**: Service to create and link nodes in Neo4j

**Input**:
- Extracted entities
- Chunk metadata
- Relationship rules

**Output**:
- `backend/services/graph_builder.py`
- Node creation logic
- Relationship mapping

**Guidelines**:
```python
class GraphBuilder:
    async def create_entity_nodes(self, entities: List[Entity], chunk_id: str):
        # Use MERGE to avoid duplicates
        # Create chunk node
        # Link entities to chunk
        # Infer relationships between entities
```

**Test Scenario**:
```cypher
# After processing
MATCH (c:AudioChunk {id: 'test-chunk-1'})
MATCH (c)-[:MENTIONS]->(p:Person)
RETURN c, p
# Should show chunk connected to person entities
```

---

### Task 14: Create Dual-Database Ingestion Pipeline
**Description**: Orchestrate data flow to both databases

**Input**:
- Processed transcript chunks
- Extracted entities
- Embeddings

**Output**:
- `backend/services/ingestion_pipeline.py`
- Coordinated storage logic
- Transaction management

**Guidelines**:
```python
class IngestionPipeline:
    async def ingest_transcript(self, audio_id: str, chunks: List[Chunk]):
        # 1. Begin PostgreSQL transaction
        # 2. Store chunks in ChromaDB with embeddings
        # 3. Create graph nodes in Neo4j
        # 4. Update PostgreSQL with completion status
        # 5. Commit or rollback
```

**Test Scenario**:
```python
pipeline = IngestionPipeline()
await pipeline.ingest_transcript("audio-123", test_chunks)
# Verify data in all three databases
# Test rollback on failure
```

---

# Phase 2: Intelligent Retrieval & Chat Integration (Weeks 5-7)

## Context Aggregation

### Task 15: Create Base Retrieval Interface
**Description**: Define common interface for retrieval services

**Input**:
- Query parameters
- Filter criteria
- Result limit

**Output**:
- `backend/services/retrieval/base.py`
- Abstract base class
- Common result format

**Guidelines**:
```python
class BaseRetriever(ABC):
    @abstractmethod
    async def search(self, query: str, filters: Dict, limit: int) -> List[Result]:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Result]:
        pass
```

**Test Scenario**:
```python
# Ensure all retrievers implement interface
assert issubclass(ChromaDBRetriever, BaseRetriever)
assert issubclass(Neo4jRetriever, BaseRetriever)
```

---

### Task 16: Implement ChromaDB Retriever
**Description**: Semantic search implementation for ChromaDB

**Input**:
- Query text
- User ID
- Date range filters
- Tag filters

**Output**:
- `backend/services/retrieval/chromadb_retriever.py`
- Ranked results with scores
- Metadata preservation

**Guidelines**:
```python
class ChromaDBRetriever(BaseRetriever):
    async def search(self, query: str, filters: Dict, limit: int = 10):
        # Generate query embedding
        # Apply metadata filters
        # Return results with:
        # - chunk text
        # - similarity score
        # - metadata (audio_id, timestamp, etc.)
```

**Test Scenario**:
```python
retriever = ChromaDBRetriever()
results = await retriever.search(
    query="project deadline",
    filters={"user_id": "test", "date_from": "2024-01-01"},
    limit=5
)
assert len(results) <= 5
assert all(r.score >= 0.7 for r in results)  # Relevance threshold
```

---

### Task 17: Implement Neo4j Graph Retriever
**Description**: Graph traversal queries for Neo4j

**Input**:
- Entity name or ID
- Relationship depth
- Relationship types

**Output**:
- `backend/services/retrieval/neo4j_retriever.py`
- Connected entities
- Relationship paths

**Guidelines**:
```cypher
# Example queries:
# Find all chunks mentioning a person
MATCH (p:Person {name: $name})<-[:MENTIONS]-(c:AudioChunk)
RETURN c

# Find related topics within 2 hops
MATCH (start:Topic {name: $topic})-[*1..2]-(related)
RETURN DISTINCT related
```

**Test Scenario**:
```python
retriever = Neo4jRetriever()
# Test entity search
results = await retriever.find_entity_mentions("John Doe")
# Test relationship traversal
connections = await retriever.find_connections("ProjectX", depth=2)
```

---

### Task 18: Create Context Aggregator Service
**Description**: Combine results from both retrieval services

**Input**:
- User query
- Retrieval strategies
- Weighting parameters

**Output**:
- `backend/services/context_aggregator.py`
- Unified context format
- Relevance scoring

**Guidelines**:
```python
class ContextAggregator:
    def __init__(self):
        self.chromadb_retriever = ChromaDBRetriever()
        self.neo4j_retriever = Neo4jRetriever()
    
    async def build_context(self, query: str, user_id: str):
        # 1. Semantic search in ChromaDB
        # 2. Extract entities from query
        # 3. Graph search in Neo4j
        # 4. Merge and deduplicate results
        # 5. Rank by combined relevance
```

**Test Scenario**:
```python
aggregator = ContextAggregator()
context = await aggregator.build_context(
    query="What did John say about the budget?",
    user_id="test"
)
# Should include both semantic matches and entity relationships
assert 'chromadb_results' in context
assert 'graph_connections' in context
```

---

### Task 19: Implement Context Ranking Algorithm
**Description**: Score and rank aggregated results

**Input**:
- Multiple result sources
- Relevance scores
- Recency factors

**Output**:
- `backend/services/context_ranker.py`
- Unified ranking score
- Explanation metadata

**Guidelines**:
```python
class ContextRanker:
    def rank_results(self, results: List[ContextResult]) -> List[RankedResult]:
        # Factors:
        # - Semantic similarity (0.4 weight)
        # - Graph centrality (0.3 weight)
        # - Recency (0.2 weight)
        # - Entity overlap (0.1 weight)
```

**Test Scenario**:
```python
ranker = ContextRanker()
ranked = ranker.rank_results(mixed_results)
# Verify ordering
assert ranked[0].score > ranked[1].score
# Verify score explanation
assert 'score_breakdown' in ranked[0].metadata
```

---

## Chat Integration

### Task 20: Update Chat Orchestrator
**Description**: Integrate context aggregator into chat flow

**Input**:
- Existing orchestrator code
- Context aggregator service
- User message

**Output**:
- Updated `backend/core/orchestrator.py`
- Rich context inclusion
- Performance optimization

**Guidelines**:
```python
# In orchestrator.py
async def process_message(self, message: str, user_id: str):
    # 1. Build context using aggregator
    context = await self.context_aggregator.build_context(message, user_id)
    
    # 2. Format context for LLM
    formatted_context = self.format_context(context)
    
    # 3. Generate response with context
    response = await self.llm_service.generate(message, formatted_context)
```

**Test Scenario**:
```python
# Mock context aggregator
# Send message referencing past audio
response = await orchestrator.process_message(
    "What was that idea I mentioned last week?",
    user_id="test"
)
# Verify context was included in LLM prompt
```

---

### Task 21: Create Context Formatting Service
**Description**: Format aggregated context for LLM consumption

**Input**:
- Raw context results
- Token limits
- Priority rules

**Output**:
- `backend/services/context_formatter.py`
- Formatted context string
- Token count management

**Guidelines**:
```python
class ContextFormatter:
    def format_for_llm(self, context: AggregatedContext, max_tokens: int = 2000):
        # Format template:
        """
        ## Relevant Audio Transcripts:
        [Timestamp] - [Summary]
        
        ## Related Entities:
        - Person: [Name] (mentioned in [N] conversations)
        
        ## Connected Topics:
        - [Topic]: [Relationship]
        """
```

**Test Scenario**:
```python
formatter = ContextFormatter()
formatted = formatter.format_for_llm(test_context, max_tokens=1000)
# Verify token count
assert count_tokens(formatted) <= 1000
# Verify structure
assert "## Relevant Audio Transcripts:" in formatted
```

---

### Task 22: Implement Query Enhancement Service
**Description**: Enhance user queries for better retrieval

**Input**:
- User query
- Chat history
- User profile

**Output**:
- `backend/services/query_enhancer.py`
- Enhanced query
- Extracted intent

**Guidelines**:
```python
class QueryEnhancer:
    async def enhance_query(self, query: str, history: List[Message]):
        # 1. Resolve pronouns using history
        # 2. Expand abbreviations
        # 3. Add temporal context
        # 4. Extract implicit entities
        # Example: "What about that?" -> "What about the budget discussion?"
```

**Test Scenario**:
```python
enhancer = QueryEnhancer()
enhanced = await enhancer.enhance_query(
    "What did he say?",
    history=[Message("John presented the budget")]
)
assert "John" in enhanced.query
assert enhanced.entities == ["John"]
```

---

### Task 23: Create Response Enhancement Service
**Description**: Enhance LLM responses with rich formatting

**Input**:
- LLM response
- Context sources
- User preferences

**Output**:
- `backend/services/response_enhancer.py`
- Enhanced response with citations
- Markdown formatting

**Guidelines**:
```python
class ResponseEnhancer:
    def enhance_response(self, response: str, context: AggregatedContext):
        # Add:
        # - Source citations [1]
        # - Related topic links
        # - Suggested follow-ups
        # - Timestamp references
```

**Test Scenario**:
```python
enhancer = ResponseEnhancer()
enhanced = enhancer.enhance_response(
    "The budget was discussed last week",
    context_with_sources
)
assert "[1]" in enhanced  # Citation
assert "Source:" in enhanced  # Source reference
```

---

# Phase 3: Plugin Ecosystem & User Insights (Weeks 8-10)

## Plugin Architecture

### Task 24: Create Plugin Base Interface
**Description**: Define plugin system architecture

**Input**:
- Plugin requirements
- Lifecycle hooks
- Security considerations

**Output**:
- `backend/plugins/base.py`
- Plugin interface definition
- Registration mechanism

**Guidelines**:
```python
class BasePlugin(ABC):
    metadata = {
        'name': str,
        'version': str,
        'description': str,
        'author': str
    }
    
    @abstractmethod
    async def initialize(self, context: PluginContext):
        pass
    
    @abstractmethod
    async def execute(self, request: PluginRequest) -> PluginResponse:
        pass
```

**Test Scenario**:
```python
# Create test plugin
class TestPlugin(BasePlugin):
    metadata = {'name': 'test', 'version': '1.0.0'}
    
# Verify interface compliance
assert hasattr(TestPlugin, 'initialize')
assert hasattr(TestPlugin, 'execute')
```

---

### Task 25: Implement Plugin Manager
**Description**: Core plugin management system

**Input**:
- Plugin directory path
- Configuration files
- Security policies

**Output**:
- `backend/plugins/manager.py`
- Dynamic plugin loading
- Lifecycle management

**Guidelines**:
```python
class PluginManager:
    def __init__(self, plugin_dir: str):
        self.plugins = {}
        self.plugin_dir = plugin_dir
    
    async def load_plugins(self):
        # Scan plugin directory
        # Validate plugin structure
        # Initialize plugins
        # Register in registry
    
    async def execute_plugin(self, name: str, request: dict):
        # Get plugin
        # Validate request
        # Execute with timeout
        # Handle errors
```

**Test Scenario**:
```python
manager = PluginManager("/plugins")
await manager.load_plugins()
assert 'review_reflection' in manager.plugins
result = await manager.execute_plugin('review_reflection', {})
```

---

### Task 26: Create Plugin Security Sandbox
**Description**: Implement security measures for plugins

**Input**:
- Resource limits
- API access controls
- Data access policies

**Output**:
- `backend/plugins/sandbox.py`
- Execution isolation
- Resource monitoring

**Guidelines**:
```python
class PluginSandbox:
    def __init__(self, plugin: BasePlugin):
        self.resource_limits = {
            'memory': '256MB',
            'cpu': '1 core',
            'timeout': 30  # seconds
        }
    
    async def execute_safe(self, request: PluginRequest):
        # Set resource limits
        # Monitor execution
        # Enforce timeouts
        # Audit access
```

**Test Scenario**:
```python
# Test resource limits
sandbox = PluginSandbox(test_plugin)
# Should timeout
with pytest.raises(TimeoutError):
    await sandbox.execute_safe(long_running_request)
```

---

### Task 27: Implement Plugin Configuration System
**Description**: Configuration management for plugins

**Input**:
- Plugin metadata
- User preferences
- System defaults

**Output**:
- `backend/plugins/config.py`
- Configuration schema
- Validation logic

**Guidelines**:
```yaml
# Plugin configuration format
plugin_name:
  enabled: true
  settings:
    schedule: "weekly"
    include_categories: ["work", "personal"]
  permissions:
    - read_transcripts
    - write_summaries
```

**Test Scenario**:
```python
config = PluginConfig.load('review_reflection')
assert config.is_enabled
assert config.get_setting('schedule') == 'weekly'
config.validate()  # Should pass
```

---

## Review & Reflection Plugin

### Task 28: Create Review Plugin Core Logic
**Description**: Implement the review and reflection plugin

**Input**:
- Time period (week/month)
- User ID
- Categories filter

**Output**:
- `backend/plugins/review_reflection/plugin.py`
- Analysis results
- Formatted insights

**Guidelines**:
```python
class ReviewReflectionPlugin(BasePlugin):
    async def analyze_period(self, start_date: date, end_date: date, user_id: str):
        # 1. Retrieve all transcripts in period
        # 2. Extract key themes
        # 3. Identify patterns
        # 4. Generate insights
        # 5. Create summary report
```

**Test Scenario**:
```python
plugin = ReviewReflectionPlugin()
results = await plugin.analyze_period(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 7),
    user_id="test"
)
assert 'themes' in results
assert 'insights' in results
assert 'summary' in results
```

---

### Task 29: Implement Theme Extraction Algorithm
**Description**: Extract recurring themes from transcripts

**Input**:
- Multiple transcript texts
- Language
- Minimum frequency

**Output**:
- `backend/plugins/review_reflection/theme_extractor.py`
- Theme clusters
- Frequency counts

**Guidelines**:
```python
class ThemeExtractor:
    def extract_themes(self, transcripts: List[str]) -> List[Theme]:
        # 1. Tokenize and clean text
        # 2. Extract noun phrases
        # 3. Cluster similar concepts
        # 4. Calculate frequencies
        # 5. Rank by importance
```

**Test Scenario**:
```python
extractor = ThemeExtractor()
themes = extractor.extract_themes(test_transcripts)
# Should identify repeated topics
assert any(t.name == "project deadline" for t in themes)
assert themes[0].frequency > themes[1].frequency  # Ordered
```

---

### Task 30: Create Insight Generation Service
**Description**: Generate actionable insights from patterns

**Input**:
- Extracted themes
- Entity relationships
- Temporal patterns

**Output**:
- `backend/plugins/review_reflection/insight_generator.py`
- Categorized insights
- Confidence scores

**Guidelines**:
```python
class InsightGenerator:
    def generate_insights(self, analysis_data: AnalysisData) -> List[Insight]:
        # Insight types:
        # - Recurring concerns
        # - Progress on goals
        # - Relationship patterns
        # - Time allocation
        # - Emotional patterns
```

**Test Scenario**:
```python
generator = InsightGenerator()
insights = generator.generate_insights(test_analysis)
# Should have different categories
assert any(i.category == 'recurring_concern' for i in insights)
assert all(0 <= i.confidence <= 1 for i in insights)
```

---

### Task 31: Implement Report Formatter
**Description**: Format analysis results for display

**Input**:
- Analysis results
- User preferences
- Output format

**Output**:
- `backend/plugins/review_reflection/report_formatter.py`
- Markdown formatted report
- Section organization

**Guidelines**:
```markdown
# Weekly Review: Jan 1-7, 2024

## 🎯 Key Themes
1. **Project Management** (mentioned 15 times)
2. **Team Communication** (mentioned 8 times)

## 💡 Insights
### Recurring Topics
- You frequently discussed deadlines...

## 📈 Progress Tracking
- Completed: [Task mentions]

## 🔄 Patterns Noticed
- Peak productivity on Tuesdays...
```

**Test Scenario**:
```python
formatter = ReportFormatter()
report = formatter.format_report(analysis_results)
assert "# Weekly Review" in report
assert "## 🎯 Key Themes" in report
# Verify markdown structure
```

---

## API Integration

### Task 32: Create Plugin API Router
**Description**: REST API endpoints for plugin access

**Input**:
- Plugin manager instance
- Authentication middleware
- Request schemas

**Output**:
- `backend/api/plugin_router.py`
- RESTful endpoints
- OpenAPI documentation

**Guidelines**:
```python
router = APIRouter(prefix="/plugins", tags=["plugins"])

@router.get("/list")
async def list_plugins():
    # Return available plugins
    
@router.post("/{plugin_name}/execute")
async def execute_plugin(plugin_name: str, request: PluginRequest):
    # Validate and execute

@router.get("/review/weekly")
async def get_weekly_review(user_id: str = Depends(get_current_user)):
    # Execute review plugin
```

**Test Scenario**:
```python
# Test API endpoints
response = client.get("/plugins/list")
assert response.status_code == 200
assert 'review_reflection' in response.json()

# Execute plugin
response = client.post("/plugins/review_reflection/execute", json={})
assert response.status_code == 200
```

---

### Task 33: Implement Plugin WebSocket Support
**Description**: Real-time plugin execution updates

**Input**:
- WebSocket connection
- Plugin execution events
- Progress updates

**Output**:
- `backend/api/plugin_websocket.py`
- Event streaming
- Progress notifications

**Guidelines**:
```python
@app.websocket("/plugins/ws/{plugin_name}")
async def plugin_websocket(websocket: WebSocket, plugin_name: str):
    await websocket.accept()
    
    async def progress_callback(progress: int, message: str):
        await websocket.send_json({
            "type": "progress",
            "progress": progress,
            "message": message
        })
```

**Test Scenario**:
```python
# Test WebSocket connection
async with websockets.connect("ws://localhost/plugins/ws/review") as ws:
    await ws.send(json.dumps({"action": "start"}))
    message = await ws.recv()
    assert json.loads(message)["type"] == "progress"
```

---

## Frontend Integration

### Task 34: Create Plugin UI Components
**Description**: Flutter widgets for plugin interaction

**Input**:
- Plugin metadata
- UI/UX requirements
- Material Design guidelines

**Output**:
- `lib/widgets/plugin_card.dart`
- `lib/widgets/plugin_executor.dart`
- Plugin listing UI

**Guidelines**:
```dart
class PluginCard extends StatelessWidget {
  final Plugin plugin;
  
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(plugin.icon),
        title: Text(plugin.name),
        subtitle: Text(plugin.description),
        trailing: Switch(
          value: plugin.enabled,
          onChanged: (_) => togglePlugin(),
        ),
      ),
    );
  }
}
```

**Test Scenario**:
```dart
// Widget test
testWidgets('PluginCard displays correctly', (tester) async {
  await tester.pumpWidget(PluginCard(testPlugin));
  expect(find.text('Review & Reflection'), findsOneWidget);
  expect(find.byType(Switch), findsOneWidget);
});
```

---

### Task 35: Implement Review Screen
**Description**: Dedicated screen for review plugin results

**Input**:
- Review data model
- Navigation flow
- Display requirements

**Output**:
- `lib/screens/review_screen.dart`
- `lib/models/review_model.dart`
- Result visualization

**Guidelines**:
```dart
class ReviewScreen extends ConsumerWidget {
  Widget build(BuildContext context, WidgetRef ref) {
    final reviewData = ref.watch(reviewProvider);
    
    return Scaffold(
      appBar: AppBar(title: Text('Weekly Review')),
      body: reviewData.when(
        data: (data) => ReviewContent(data),
        loading: () => CircularProgressIndicator(),
        error: (err, stack) => ErrorWidget(err),
      ),
    );
  }
}
```

**Test Scenario**:
```dart
// Integration test
await tester.pumpWidget(ReviewScreen());
await tester.pumpAndSettle();
expect(find.text('Key Themes'), findsOneWidget);
expect(find.byType(ThemeChart), findsOneWidget);
```

---

### Task 36: Create Plugin State Management
**Description**: Riverpod providers for plugin data

**Input**:
- Plugin API client
- State requirements
- Cache strategy

**Output**:
- `lib/providers/plugin_provider.dart`
- State notifications
- Data persistence

**Guidelines**:
```dart
final pluginListProvider = FutureProvider<List<Plugin>>((ref) async {
  final client = ref.watch(apiClientProvider);
  return client.getPlugins();
});

final reviewProvider = StateNotifierProvider<ReviewNotifier, AsyncValue<ReviewData>>((ref) {
  return ReviewNotifier(ref.watch(apiClientProvider));
});
```

**Test Scenario**:
```dart
// Provider test
final container = ProviderContainer();
final plugins = await container.read(pluginListProvider.future);
expect(plugins.length, greaterThan(0));
```

---

## Testing & Validation

### Task 37: Create Integration Test Suite
**Description**: End-to-end testing for dual-memory system

**Input**:
- Test scenarios
- Test data
- Performance benchmarks

**Output**:
- `backend/tests/integration/test_dual_memory.py`
- Performance reports
- Coverage metrics

**Guidelines**:
```python
class TestDualMemoryIntegration:
    async def test_audio_processing_pipeline(self):
        # 1. Submit audio for processing
        # 2. Verify transcription
        # 3. Check ChromaDB storage
        # 4. Verify Neo4j nodes
        # 5. Test retrieval
    
    async def test_context_aggregation(self):
        # Test combined retrieval
        # Verify ranking
        # Check performance
```

**Test Scenario**:
```bash
pytest backend/tests/integration/test_dual_memory.py
# All tests should pass
# Performance: < 2s for full pipeline
```

---

### Task 38: Implement Load Testing
**Description**: Performance testing under load

**Input**:
- Concurrent user scenarios
- Data volume targets
- Response time SLAs

**Output**:
- `backend/tests/load/locustfile.py`
- Performance metrics
- Bottleneck analysis

**Guidelines**:
```python
class TranscriptUser(HttpUser):
    @task
    def process_transcript(self):
        # Simulate audio upload
        # Monitor processing time
        # Check retrieval performance
    
    @task
    def search_context(self):
        # Simulate searches
        # Measure response times
```

**Test Scenario**:
```bash
locust -f locustfile.py --users 100 --spawn-rate 10
# Target: 95% requests < 1s
# No errors under 100 concurrent users
```

---

### Task 39: Create Data Validation Suite
**Description**: Validate data integrity across databases

**Input**:
- Database schemas
- Consistency rules
- Data samples

**Output**:
- `backend/tests/validation/data_validator.py`
- Validation reports
- Repair scripts

**Guidelines**:
```python
class DataValidator:
    async def validate_consistency(self):
        # Check PostgreSQL audio records
        # Verify ChromaDB chunks match
        # Validate Neo4j relationships
        # Report orphaned data
    
    async def validate_user_isolation(self):
        # Ensure no data leakage
        # Verify user_id filtering
```

**Test Scenario**:
```python
validator = DataValidator()
report = await validator.validate_consistency()
assert report.errors == []
assert report.warnings <= acceptable_threshold
```

---

### Task 40: Implement Monitoring Dashboard
**Description**: System health monitoring

**Input**:
- Metrics collection points
- Alert thresholds
- Dashboard requirements

**Output**:
- `backend/monitoring/metrics.py`
- Grafana dashboard config
- Alert rules

**Guidelines**:
```python
# Metrics to track:
# - Processing queue length
# - Average processing time
# - Database query latency
# - Memory usage per service
# - Error rates by type

prometheus_metrics = {
    'transcript_processing_duration': Histogram(),
    'context_retrieval_latency': Histogram(),
    'active_plugins': Gauge(),
}
```

**Test Scenario**:
```bash
# Verify metrics endpoint
curl http://localhost:8000/metrics
# Check Prometheus scraping
# Verify Grafana dashboards load
```

---

## Documentation & Deployment

### Task 41: Create API Documentation
**Description**: Comprehensive API documentation

**Input**:
- OpenAPI schemas
- Example requests
- Authentication flow

**Output**:
- `docs/API_REFERENCE.md`
- Postman collection
- Interactive docs

**Guidelines**:
```markdown
# Pegasus Brain API Reference

## Authentication
All requests require Bearer token...

## Endpoints

### POST /audio/process
Process uploaded audio file
```

**Test Scenario**:
```bash
# Generate OpenAPI spec
python -m backend.generate_openapi > openapi.json
# Validate spec
swagger-cli validate openapi.json
```

---

### Task 42: Write Deployment Guide
**Description**: Production deployment documentation

**Input**:
- Infrastructure requirements
- Configuration steps
- Security checklist

**Output**:
- `docs/DEPLOYMENT_GUIDE.md`
- Docker compose production
- Kubernetes manifests

**Guidelines**:
```markdown
# Production Deployment Guide

## Prerequisites
- Docker 20.10+
- 8GB RAM minimum
- 50GB storage

## Steps
1. Configure environment
2. Initialize databases
3. Deploy services
```

**Test Scenario**:
```bash
# Test deployment steps
docker-compose -f docker-compose.prod.yml up -d
# Verify all services healthy
./scripts/health_check.sh
```

---

## Summary

This implementation plan consists of **42 detailed tasks** organized across three phases:

**Phase 1 (Tasks 1-14)**: Foundation - Infrastructure, workers, NER, dual-database
**Phase 2 (Tasks 15-23)**: Retrieval & Integration - Context aggregation, chat enhancement  
**Phase 3 (Tasks 24-42)**: Plugins & Polish - Plugin system, Review plugin, testing, deployment

Each task is:
- **Small and focused** (1-3 days of work)
- **Independently testable** 
- **Clearly defined** with inputs, outputs, and test scenarios
- **Sequentially dependent** where necessary

The plan follows the refined architecture exactly, implementing the dual-memory system with ChromaDB for semantic search and Neo4j for relationship mapping, all orchestrated through a resilient job queue system with plugin extensibility.