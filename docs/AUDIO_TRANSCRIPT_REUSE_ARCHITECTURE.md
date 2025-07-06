# Design Architecture Plan: Audio Transcript Reuse for Pegasus AI Assistant

## Executive Summary

This document proposes a comprehensive architecture to integrate audio transcripts into Pegasus's vector database system, enabling the AI assistant to leverage past conversations and recordings as part of its "second brain" functionality. The design aligns with Pegasus's ultimate goal of serving as a contextual memory system that reduces mental load and provides proactive support.

## Table of Contents

1. [Project Context & Goals](#project-context--goals)
2. [Current State Analysis](#current-state-analysis)
3. [Proposed Architecture](#proposed-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Technical Design Details](#technical-design-details)
6. [Use Cases & Benefits](#use-cases--benefits)
7. [Privacy & Security Considerations](#privacy--security-considerations)
8. [Success Metrics](#success-metrics)

---

## Project Context & Goals

### Pegasus Vision
Pegasus aims to be a personal AI assistant that acts as a "second brain," helping users:
- Organize scattered thoughts into actionable plans
- Remember important information from conversations
- Provide contextual, proactive support
- Reduce mental load through intelligent assistance

### Strategic Objective
Transform stored audio transcripts from passive archives into active knowledge that enhances the AI's ability to understand user context, recall past conversations, and provide more personalized assistance.

---

## Current State Analysis

### Existing Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                     Current Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Flutter App ──► FastAPI Backend ──► Audio Storage         │
│      │               │                    │                 │
│      │               │                    ▼                 │
│      │               │              PostgreSQL DB           │
│      │               │              (Transcripts)           │
│      │               │                                      │
│      │               ▼                                      │
│      │         Ollama Service                              │
│      │         (Improvement)                               │
│      │                                                      │
│      └──────► Chat Interface ◄──── ChromaDB               │
│                                    (No Audio)              │
│                                                             │
│  Separate: Data Pipeline ──► ChromaDB                      │
│            (source_data/)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Gaps
1. Audio transcripts are not indexed in ChromaDB
2. Chat context doesn't include past audio recordings
3. No semantic search across audio content
4. Limited proactive insights from recorded thoughts

---

## Proposed Architecture

### Enhanced System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    Proposed Architecture                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Flutter App ──► FastAPI Backend ──► Audio Storage             │
│      │               │                    │                     │
│      │               │                    ▼                     │
│      │               │              PostgreSQL DB               │
│      │               │              (Full Transcripts)          │
│      │               │                    │                     │
│      │               │                    ▼                     │
│      │               │           Transcript Processor           │
│      │               │           ┌────────────────┐            │
│      │               │           │ • Chunking     │            │
│      │               │           │ • Embedding    │            │
│      │               │           │ • Metadata     │            │
│      │               │           └────────┬───────┘            │
│      │               │                    ▼                     │
│      │               ▼              ChromaDB                    │
│      │         Enhanced Chat ◄─── (Audio + Docs)               │
│      │         Orchestrator                                     │
│      │               │                                          │
│      │               ▼                                          │
│      └──────► Contextual AI                                    │
│               Responses                                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐          │
│  │         New Components                           │          │
│  ├─────────────────────────────────────────────────┤          │
│  │ • Memory Graph Builder                          │          │
│  │ • Insight Generator                             │          │
│  │ • Context Aggregator                            │          │
│  │ • Proactive Agent                               │          │
│  └─────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. **Transcript Processing Pipeline**
- Automatic triggering when transcription completes
- Intelligent chunking based on semantic boundaries
- Metadata enrichment (date, time, tags, context)
- Multi-language embedding generation

#### 2. **Enhanced Vector Storage**
- Unified collection for audio transcripts and documents
- Rich metadata filtering capabilities
- Temporal indexing for chronological queries
- Tag-based categorization

#### 3. **Memory Graph System**
- Builds connections between related conversations
- Tracks topic evolution over time
- Identifies recurring themes and concerns
- Maintains user preference patterns

#### 4. **Proactive Intelligence Engine**
- Analyzes patterns in stored conversations
- Generates insights and suggestions
- Triggers contextual reminders
- Surfaces relevant past discussions

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Establish core infrastructure for transcript vectorization

1. **Backend Enhancement**
   ```python
   # New service: backend/services/transcript_vectorizer.py
   class TranscriptVectorizer:
       async def process_transcript(audio_id: str):
           - Load transcript from database
           - Chunk into semantic segments
           - Generate embeddings
           - Store in ChromaDB with metadata
   ```

2. **Database Schema Update**
   ```sql
   ALTER TABLE audio_files ADD COLUMN vector_indexed BOOLEAN DEFAULT FALSE;
   ALTER TABLE audio_files ADD COLUMN vector_indexed_at TIMESTAMP;
   ```

3. **Background Task Integration**
   - Hook into existing transcription completion
   - Queue vectorization as async task
   - Update status tracking

### Phase 2: Intelligent Chunking (Weeks 3-4)
**Goal**: Develop smart chunking strategies for better retrieval

1. **Semantic Chunker**
   ```python
   class SemanticChunker:
       def chunk_transcript(text: str, language: str):
           - Identify natural conversation breaks
           - Preserve context windows
           - Handle multi-topic discussions
           - Maintain speaker intent
   ```

2. **Metadata Enrichment**
   - Extract topics, entities, dates mentioned
   - Identify action items and decisions
   - Tag emotional context
   - Link related conversations

### Phase 3: Enhanced Retrieval (Weeks 5-6)
**Goal**: Upgrade chat orchestrator with audio context

1. **Context Aggregator**
   ```python
   class ContextAggregator:
       async def build_context(query: str, user_id: str):
           - Query ChromaDB for relevant chunks
           - Combine audio transcripts + documents
           - Apply temporal weighting
           - Filter by user preferences
   ```

2. **Relevance Scoring**
   - Recency bias for recent conversations
   - Tag matching for categorical search
   - Semantic similarity threshold tuning
   - Context window optimization

### Phase 4: Memory Graph (Weeks 7-8)
**Goal**: Build relationship mapping between conversations

1. **Graph Builder**
   ```python
   class MemoryGraphBuilder:
       def build_connections(user_id: str):
           - Analyze all user transcripts
           - Identify topic clusters
           - Map temporal relationships
           - Track conversation threads
   ```

2. **Insight Generation**
   - Pattern recognition across conversations
   - Theme evolution tracking
   - Concern identification
   - Progress monitoring

### Phase 5: Proactive Features (Weeks 9-10)
**Goal**: Enable proactive assistance based on audio history

1. **Proactive Agent**
   ```python
   class ProactiveAgent:
       async def generate_insights(user_id: str):
           - Analyze recent conversations
           - Identify unresolved topics
           - Generate follow-up suggestions
           - Create contextual reminders
   ```

2. **Notification System**
   - Smart timing for reminders
   - Context-aware suggestions
   - Progress check-ins
   - Celebration of achievements

---

## Technical Design Details

### Data Models

#### Enhanced Audio Metadata
```python
class AudioTranscriptMetadata:
    audio_id: str
    user_id: str
    timestamp: datetime
    language: str
    tags: List[str]
    topics: List[str]  # Auto-extracted
    entities: List[str]  # Names, places, etc.
    sentiment: float  # Emotional context
    action_items: List[str]  # Extracted tasks
    questions: List[str]  # Unresolved queries
```

#### Vector Storage Schema
```python
class TranscriptChunk:
    id: str
    audio_id: str
    text: str
    embedding: List[float]
    metadata: AudioTranscriptMetadata
    chunk_index: int
    chunk_context: str  # Surrounding text
```

### API Endpoints

#### New Endpoints
```python
# Search across audio transcripts
POST /api/audio/search
{
    "query": "discussion about project deadlines",
    "user_id": "user123",
    "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
    "tags": ["work", "planning"]
}

# Get conversation insights
GET /api/insights/{user_id}
Response: {
    "recurring_themes": [...],
    "unresolved_topics": [...],
    "action_items": [...],
    "conversation_patterns": [...]
}

# Get related conversations
GET /api/audio/{audio_id}/related
Response: {
    "related_conversations": [...],
    "common_topics": [...],
    "temporal_connections": [...]
}
```

### Integration Points

#### 1. Transcription Service Enhancement
```python
# backend/services/transcription_service.py
async def process_transcription_complete(audio_id: str):
    # Existing: Update database with transcript
    await audio_repository.update_transcript(...)
    
    # New: Trigger vectorization
    await transcript_vectorizer.process_transcript(audio_id)
    
    # New: Update memory graph
    await memory_graph.add_conversation(audio_id)
```

#### 2. Chat Orchestrator Upgrade
```python
# backend/core/orchestrator.py
async def build_context(message: str, user_id: str):
    # Enhanced context retrieval
    context_parts = []
    
    # Get relevant audio transcripts
    audio_context = await vector_db.search_audio_transcripts(
        query=message,
        user_id=user_id,
        limit=5
    )
    context_parts.extend(audio_context)
    
    # Get relevant documents (existing)
    doc_context = await vector_db.search_documents(...)
    context_parts.extend(doc_context)
    
    # Get conversation insights
    insights = await insight_generator.get_relevant_insights(
        message=message,
        user_id=user_id
    )
    
    return format_enhanced_context(context_parts, insights)
```

### Storage Optimization

#### Chunking Strategy
```python
def intelligent_chunk_transcript(transcript: str, target_size: int = 500):
    chunks = []
    
    # 1. Split by natural breaks (paragraphs, speaker turns)
    segments = split_by_natural_breaks(transcript)
    
    # 2. Combine small segments, split large ones
    for segment in segments:
        if len(segment) < target_size * 0.5:
            # Combine with adjacent segments
            chunks = combine_small_segments(chunks, segment)
        elif len(segment) > target_size * 1.5:
            # Split intelligently at sentence boundaries
            chunks.extend(split_large_segment(segment, target_size))
        else:
            chunks.append(segment)
    
    # 3. Add context overlap between chunks
    chunks = add_context_overlap(chunks, overlap_size=50)
    
    return chunks
```

#### Embedding Generation
```python
async def generate_embeddings(chunks: List[str], metadata: dict):
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        # Generate embedding with context
        context_text = f"{metadata['tags']} {metadata['date']} {chunk}"
        embedding = await embedding_model.encode(context_text)
        
        embeddings.append({
            'text': chunk,
            'embedding': embedding,
            'metadata': {
                **metadata,
                'chunk_index': i,
                'chunk_total': len(chunks)
            }
        })
    
    return embeddings
```

---

## Use Cases & Benefits

### 1. **Contextual Conversation Continuity**
**Scenario**: User mentions "that idea we discussed last week"
**System Response**: AI retrieves relevant audio transcript and continues conversation with full context

### 2. **Thought Evolution Tracking**
**Scenario**: User exploring a business idea over multiple recordings
**System Response**: AI shows how the idea has evolved, identifies progress, suggests next steps

### 3. **Intelligent Reminders**
**Scenario**: User mentioned a deadline in a voice note
**System Response**: Proactive reminder with original context as deadline approaches

### 4. **Pattern Recognition**
**Scenario**: User frequently discusses work stress
**System Response**: AI recognizes pattern, offers support strategies, tracks improvement

### 5. **Cross-Reference Intelligence**
**Scenario**: User asks about a topic mentioned in various contexts
**System Response**: AI synthesizes information from multiple conversations and documents

### 6. **Personal Growth Insights**
**Scenario**: Monthly reflection on recorded thoughts
**System Response**: AI generates insights on achievements, challenges overcome, and growth areas

---

## Privacy & Security Considerations

### Data Protection Measures

1. **Encryption**
   - All transcripts encrypted at rest
   - Secure embedding generation
   - Encrypted vector storage

2. **Access Control**
   - Strict user_id filtering
   - No cross-user data access
   - Audit logging for all queries

3. **Data Retention**
   - User-configurable retention policies
   - Automatic purging of old vectors
   - Right to deletion support

4. **Privacy-Preserving Features**
   - Local embedding generation option
   - On-device processing capability
   - Anonymized insight generation

### Compliance Considerations

1. **GDPR Compliance**
   - Clear consent for processing
   - Data portability support
   - Deletion mechanisms

2. **Transparency**
   - User visibility into stored data
   - Processing explanation
   - Insight reasoning

---

## Success Metrics

### Technical Metrics

1. **Performance**
   - Transcript vectorization time < 2 seconds
   - Context retrieval latency < 500ms
   - Embedding accuracy > 90%

2. **Coverage**
   - 100% of new transcripts vectorized
   - Historical transcript migration rate
   - Search result relevance score

### User Experience Metrics

1. **Engagement**
   - Increased chat context relevance
   - Audio search feature usage
   - Insight interaction rate

2. **Value Delivery**
   - Task completion assistance rate
   - Memory recall accuracy
   - User satisfaction scores

### Business Impact

1. **Retention**
   - User retention improvement
   - Feature adoption rate
   - Daily active usage

2. **Differentiation**
   - Unique "second brain" capabilities
   - Competitive advantage metrics
   - User testimonials

---

## Implementation Roadmap

### Immediate Actions (Week 1)
1. Create `transcript_vectorizer.py` service
2. Add vector indexing to transcription pipeline
3. Update database schema
4. Begin chunking algorithm development

### Short-term Goals (Month 1)
1. Complete Phase 1 & 2 implementation
2. Deploy basic audio search functionality
3. Integrate with chat orchestrator
4. Begin user testing

### Medium-term Goals (Month 2-3)
1. Launch memory graph system
2. Deploy proactive insights
3. Implement advanced search filters
4. Optimize performance

### Long-term Vision (Month 4+)
1. Multi-modal memory integration
2. Advanced relationship mapping
3. Predictive assistance
4. Collaborative memory features

---

## Conclusion

This architecture plan transforms Pegasus's audio transcripts from passive storage into an active, intelligent memory system. By implementing these enhancements, Pegasus will truly become the "second brain" envisioned in the specifications, providing users with contextual, proactive, and deeply personalized AI assistance.

The phased approach ensures manageable implementation while delivering value incrementally. Each phase builds upon the previous, creating a robust system that respects user privacy while maximizing the utility of their recorded thoughts and conversations.

With this architecture, Pegasus will excel at its core mission: reducing mental load, enhancing memory, and providing the kind of thoughtful, context-aware support that makes AI feel like a true companion rather than just a tool.