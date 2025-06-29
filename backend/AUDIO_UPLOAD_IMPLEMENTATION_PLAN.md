# Audio Upload API Implementation Plan

## Overview

This document outlines the implementation plan for adding audio file upload and processing capabilities to the Pegasus backend API. The system will receive audio files from the frontend, store them intelligently, transcribe them using AI services, improve the transcriptions with LLM, and store all information in a PostgreSQL database.

## Architecture Overview

```
Frontend (Flutter App)
    |
    v
FastAPI Backend
    |
    +---> File Storage System
    |         |
    |         v
    |     Local Filesystem
    |         (organized by date/user)
    |
    +---> Audio Processing Pipeline
    |         |
    |         +---> Transcription Service
    |         |         |
    |         |         +---> Whisper (local)
    |         |         +---> Deepgram API (cloud)
    |         |
    |         +---> Transcript Enhancement
    |                   |
    |                   +---> Ollama LLM (local)
    |
    +---> PostgreSQL Database
              |
              +---> audio_files table
```

## Detailed Implementation Components

### 1. Database Schema

```sql
CREATE TABLE audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,
    mime_type VARCHAR(100),
    
    -- Transcription data
    original_transcript TEXT,
    improved_transcript TEXT,
    transcription_engine VARCHAR(50), -- 'whisper' or 'deepgram'
    transcription_started_at TIMESTAMP,
    transcription_completed_at TIMESTAMP,
    improvement_completed_at TIMESTAMP,
    
    -- Metadata
    user_id VARCHAR(255), -- from auth token if available
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'uploaded', -- uploaded, transcribing, improving, completed, failed
    error_message TEXT,
    
    -- Indexes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audio_files_user_id ON audio_files(user_id);
CREATE INDEX idx_audio_files_upload_timestamp ON audio_files(upload_timestamp);
CREATE INDEX idx_audio_files_status ON audio_files(processing_status);
```

### 2. File Storage Structure

```
/audio_files/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   ├── audio_20240115_143022_a1b2c3.m4a
│   │   │   └── audio_20240115_145512_d4e5f6.m4a
│   │   └── 16/
│   │       └── audio_20240116_091023_g7h8i9.m4a
│   └── 02/
│       └── ...
```

File naming convention: `audio_YYYYMMDD_HHMMSS_RANDOM.extension`

### 3. API Endpoints

#### POST /api/audio/upload
- **Purpose**: Upload audio file
- **Request**: Multipart form data
  - file: Audio file (m4a, mp3, wav, etc.)
  - timestamp: Recording timestamp (optional)
  - duration: Recording duration in seconds (optional)
- **Response**: 
  ```json
  {
    "id": "uuid",
    "status": "processing",
    "message": "Audio file uploaded successfully"
  }
  ```

#### GET /api/audio/{id}
- **Purpose**: Get audio file information and transcripts
- **Response**:
  ```json
  {
    "id": "uuid",
    "filename": "audio_20240115_143022_a1b2c3.m4a",
    "upload_timestamp": "2024-01-15T14:30:22Z",
    "status": "completed",
    "original_transcript": "...",
    "improved_transcript": "...",
    "duration_seconds": 45.5,
    "file_size_bytes": 1234567
  }
  ```

#### GET /api/audio/list
- **Purpose**: List user's audio files
- **Query params**: 
  - page: int (default: 1)
  - limit: int (default: 20)
  - status: string (filter by status)
  - from_date: date
  - to_date: date
- **Response**:
  ```json
  {
    "items": [...],
    "total": 42,
    "page": 1,
    "pages": 3
  }
  ```

#### DELETE /api/audio/{id}
- **Purpose**: Delete audio file and its records

### 4. Services Architecture

#### AudioStorageService
```python
class AudioStorageService:
    def save_audio_file(file: UploadFile) -> str:
        """Save uploaded file to organized storage"""
    
    def get_file_path(file_id: str) -> str:
        """Get full path for a file"""
    
    def delete_file(file_path: str) -> bool:
        """Delete file from storage"""
    
    def generate_unique_filename(original_name: str) -> str:
        """Generate unique filename with timestamp"""
```

#### TranscriptionService
```python
class TranscriptionService:
    def __init__(self, engine: str = "whisper"):
        self.engine = engine
    
    async def transcribe_audio(file_path: str) -> str:
        """Transcribe audio using configured engine"""
        
    async def _transcribe_with_whisper(file_path: str) -> str:
        """Local Whisper transcription"""
    
    async def _transcribe_with_deepgram(file_path: str) -> str:
        """Deepgram API transcription"""
```

#### TranscriptEnhancementService
```python
class TranscriptEnhancementService:
    def __init__(self, ollama_model: str = "llama2"):
        self.model = ollama_model
    
    async def enhance_transcript(original: str) -> str:
        """Improve transcript with LLM"""
        # Prompt engineering for transcript correction
        # Focus on punctuation and grammar only
```

#### AudioRepository
```python
class AudioRepository:
    async def create_audio_record(data: dict) -> AudioFile:
        """Create database record"""
    
    async def update_audio_record(id: str, data: dict) -> AudioFile:
        """Update record"""
    
    async def get_audio_by_id(id: str) -> AudioFile:
        """Get single record"""
    
    async def list_audio_files(filters: dict) -> List[AudioFile]:
        """List with filters"""
```

### 5. Configuration

```python
# config.py
class AudioSettings(BaseSettings):
    # Storage
    audio_storage_path: str = "./audio_files"
    max_file_size_mb: int = 100
    allowed_formats: List[str] = ["m4a", "mp3", "wav", "ogg"]
    
    # Transcription
    transcription_engine: str = "whisper"  # or "deepgram"
    whisper_model: str = "base"
    deepgram_api_key: Optional[str] = None
    
    # Enhancement
    ollama_model: str = "llama2"
    ollama_base_url: str = "http://localhost:11434"
    enhancement_prompt_template: str = """
    Correct the following transcript by adding proper punctuation and fixing 
    grammatical errors. Do not change the meaning or add new content.
    Keep the original speaker's words and style.
    
    Original transcript: {transcript}
    
    Corrected transcript:
    """
    
    # Database
    database_url: str = "postgresql://user:pass@localhost/pegasus"
```

### 6. Processing Pipeline

```python
async def process_audio_upload(file: UploadFile, user_id: Optional[str] = None):
    # 1. Validate file
    validate_audio_file(file)
    
    # 2. Save to storage
    file_path = await storage_service.save_audio_file(file)
    
    # 3. Create database record
    audio_record = await audio_repo.create_audio_record({
        "filename": file.filename,
        "file_path": file_path,
        "user_id": user_id,
        "status": "transcribing"
    })
    
    # 4. Start async processing
    background_tasks.add_task(
        process_audio_async,
        audio_record.id,
        file_path
    )
    
    return audio_record

async def process_audio_async(audio_id: str, file_path: str):
    try:
        # 1. Transcribe
        transcript = await transcription_service.transcribe_audio(file_path)
        await audio_repo.update_audio_record(audio_id, {
            "original_transcript": transcript,
            "status": "improving"
        })
        
        # 2. Enhance transcript
        improved = await enhancement_service.enhance_transcript(transcript)
        await audio_repo.update_audio_record(audio_id, {
            "improved_transcript": improved,
            "status": "completed"
        })
        
    except Exception as e:
        await audio_repo.update_audio_record(audio_id, {
            "status": "failed",
            "error_message": str(e)
        })
```

### 7. Dependencies

Add to requirements.txt:
```
# Existing...
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# Audio processing
python-multipart>=0.0.6
openai-whisper>=20231117  # for local transcription
httpx>=0.26.0  # for API calls
ollama>=0.1.7  # for LLM enhancement

# File handling
aiofiles>=23.2.1
python-magic>=0.4.27  # for MIME type detection
```

### 8. Error Handling

- File too large → Return 413 with clear message
- Invalid format → Return 400 with supported formats
- Transcription failure → Mark as failed, keep file
- LLM enhancement failure → Keep original transcript
- Database errors → Proper rollback and cleanup

### 9. Security Considerations

- Validate file types (check magic bytes, not just extension)
- Sanitize filenames
- Rate limiting on uploads
- User isolation (users can only access their own files)
- Virus scanning (optional, using ClamAV)

### 10. Testing Strategy

1. Unit tests for each service
2. Integration tests for full pipeline
3. Load testing for concurrent uploads
4. Test with various audio formats and sizes
5. Test error scenarios and recovery

## Implementation Steps

1. **Database Setup** (2 hours)
   - Create PostgreSQL database
   - Run migrations for audio_files table
   - Set up SQLAlchemy models

2. **File Storage Service** (2 hours)
   - Implement storage logic
   - Create directory structure
   - Add file validation

3. **Audio Upload Endpoint** (3 hours)
   - Create router
   - Implement file upload
   - Add validation and error handling

4. **Transcription Service** (4 hours)
   - Integrate Whisper
   - Add Deepgram API option
   - Implement fallback logic

5. **Enhancement Service** (3 hours)
   - Integrate Ollama
   - Create enhancement prompts
   - Test with various transcripts

6. **Background Processing** (2 hours)
   - Set up async task processing
   - Add status updates
   - Implement retry logic

7. **API Endpoints** (2 hours)
   - List endpoint with filters
   - Get single audio file
   - Delete functionality

8. **Testing** (3 hours)
   - Write comprehensive tests
   - Manual testing
   - Performance testing

Total estimated time: ~21 hours

## Future Enhancements

1. **Real-time Updates**
   - WebSocket for processing status
   - Progress indicators

2. **Advanced Features**
   - Speaker diarization
   - Language detection
   - Sentiment analysis
   - Keyword extraction

3. **Storage Optimization**
   - S3/Cloud storage option
   - Audio compression
   - Archival policies

4. **Analytics**
   - Usage statistics
   - Processing time metrics
   - Error rate monitoring