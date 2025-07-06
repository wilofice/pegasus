# Pegasus Data Pipeline - Enhanced Version

This enhanced pipeline provides an alternative way to ingest and process audio files by watching a folder for new files. It integrates with the existing backend audio processing logic to avoid code duplication while maintaining the file-watching capability.

## Overview

The data pipeline offers two processing modes:

### 1. **Enhanced Mode (Recommended)** - `pipeline_v2.py`
- **Full Backend Integration**: Uses the same processing logic as the API
- **Complete Workflow**: Transcription → Improvement → Vector/Graph/Entity indexing
- **Database Integration**: Stores files in the same PostgreSQL database
- **Status Tracking**: Full processing status and error handling
- **Unified Configuration**: Uses the same settings as the backend

### 2. **Legacy Mode** - `pipeline.py`
- **Simple Processing**: Basic transcription and ChromaDB storage
- **Minimal Integration**: Webhook notifications only
- **Standalone**: Independent of backend database

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure the backend is properly configured (database, settings, etc.)

## Usage

### Enhanced Pipeline (Recommended)

Start the enhanced pipeline that uses backend logic:

```bash
python pipeline_v2.py
```

Or specify a custom source folder:
```bash
python pipeline_v2.py /path/to/custom/source/folder
```

### Pipeline Management

Use the management script for monitoring and manual operations:

```bash
# Show pipeline status and configuration
python pipeline_manager.py status

# Manually process a specific file
python pipeline_manager.py process /path/to/audio.mp3 --user-id "my_user" --language "en"

# Check processing status of an audio file
python pipeline_manager.py check-status <audio-id>

# List recent processed files
python pipeline_manager.py list-recent --limit 20

# Clean old log files
python pipeline_manager.py clean-logs --days 7
```

### Legacy Pipeline

For backward compatibility:
```bash
python pipeline.py
```

## Supported Audio Formats

The pipeline supports the same audio formats as the backend API:
- `.mp3` - MPEG Audio Layer 3
- `.m4a` - MPEG-4 Audio
- `.wav` - Waveform Audio File Format
- `.ogg` - Ogg Vorbis
- `.webm` - WebM Audio
- `.aac` - Advanced Audio Coding
- `.flac` - Free Lossless Audio Codec

## File Processing Workflow

### Enhanced Pipeline Workflow

1. **File Detection**: Watchdog monitors `source_data/` folder
2. **File Storage**: Moves file to backend storage structure
3. **Database Record**: Creates AudioFile record in PostgreSQL
4. **Transcription**: Uses configured transcription engine (Whisper/Deepgram)
5. **Transcript Improvement**: Uses Ollama for text enhancement (if configured)
6. **Brain Indexing**: Celery tasks for vector/graph/entity processing
7. **Status Updates**: Comprehensive status tracking throughout
8. **Webhook Notification**: Optional notification on completion

### Language Detection

The pipeline can auto-detect language from filenames:
- `meeting_en.mp3` → English transcription
- `conversation_fr.m4a` → French transcription
- `audio.wav` → Default language (English)

## Configuration

The pipeline uses the same configuration as the backend:

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pegasus_db

# Transcription
TRANSCRIPTION_ENGINE=whisper  # or "deepgram"
WHISPER_MODEL=medium

# LLM for transcript improvement
LLM_PROVIDER=ollama  # or "google_generative_ai"
OLLAMA_MODEL=gemma3:12b
OLLAMA_BASE_URL=http://localhost:11434

# Optional webhook notifications
PIPELINE_WEBHOOK_ENABLED=true
PIPELINE_WEBHOOK_URL=http://localhost:8000/api/webhook
```

### Folder Structure
```
data_pipeline/
├── source_data/          # Drop audio files here
├── processed/            # Processed files archive
├── logs/                 # Pipeline logs
├── pipeline_v2.py        # Enhanced pipeline
├── pipeline_manager.py   # Management utilities
├── backend_integration.py # Backend integration logic
└── config.py            # Configuration management
```

## Integration with Backend

### Shared Components
- **Transcription Service**: Same Whisper/Deepgram configuration
- **Audio Storage**: Uses backend storage structure
- **Database Models**: Same AudioFile model and relationships
- **Processing Logic**: Identical transcription → improvement → indexing workflow
- **Job Tracking**: Full integration with backend job system

### Status Monitoring

Files processed through the pipeline appear in the backend API with:
- `user_id`: "data_pipeline"
- `source`: "data_pipeline"
- Full processing status tracking
- Same indexing and search capabilities

## Monitoring and Troubleshooting

### Log Files
- `logs/pipeline_v2.log` - Enhanced pipeline logs
- `logs/pipeline.log` - Legacy pipeline logs

### Status Checking
```bash
# Check overall pipeline status
python pipeline_manager.py status

# Monitor recent processing
python pipeline_manager.py list-recent

# Check specific file status
python pipeline_manager.py check-status <audio-id>
```

### Common Issues

1. **Database Connection**: Ensure backend database is running and accessible
2. **Storage Permissions**: Check write permissions for audio storage path
3. **Model Downloads**: Whisper models download automatically on first use
4. **Memory Usage**: Large audio files may require sufficient RAM for processing

## Migration from Legacy Pipeline

To migrate from the original pipeline to the enhanced version:

1. **Backup**: Archive any important ChromaDB data
2. **Switch**: Use `pipeline_v2.py` instead of `pipeline.py`
3. **Configuration**: Update environment variables to match backend
4. **Testing**: Process a few test files to verify functionality
5. **Monitoring**: Use `pipeline_manager.py` for status monitoring

## API Compatibility

Files processed through the pipeline are fully compatible with the backend API:
- Accessible via `/api/audio/` endpoints
- Same transcript retrieval and status checking
- Integrated with chat system for context search
- Full indexing in vector and graph databases

## Quick Start

1. **Setup Environment**:
```bash
cd data_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure Backend**: Ensure backend `.env` is properly configured

3. **Start Enhanced Pipeline**:
```bash
python pipeline_v2.py
```

4. **Test Processing**: Drop an audio file in `source_data/` folder

5. **Monitor Status**:
```bash
python pipeline_manager.py status
python pipeline_manager.py list-recent
```

The enhanced pipeline provides a seamless bridge between file-based ingestion and the sophisticated backend processing infrastructure, ensuring consistency and avoiding code duplication.