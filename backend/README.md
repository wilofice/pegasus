# Pegasus Backend API

Backend API for the Pegasus application, providing chat, webhook, and audio processing capabilities.

## Features

- **Chat & Webhook Endpoints**: Original Pegasus functionality
- **Audio Upload & Storage**: Secure file upload with organized storage structure
- **Transcription**: Support for both Whisper (local) and Deepgram (cloud) transcription engines
- **AI Enhancement**: Transcript improvement using Ollama local LLM
- **PostgreSQL Database**: Robust data storage with full audit trail
- **Background Processing**: Async processing pipeline for audio files
- **RESTful API**: Comprehensive API for audio file management

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Optional: Ollama for transcript enhancement
- Optional: GPU support for faster Whisper transcription

### Installation

1. **Create virtual environment and install dependencies**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database and service settings
   ```

3. **Initialize database**:
   ```bash
   python scripts/init_db.py
   ```

4. **Run the server**:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

### Optional: Setup Ollama (for transcript enhancement)

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Verify: `ollama list`

## API Endpoints

### Audio Endpoints

#### Upload Audio File
```http
POST /api/audio/upload
Content-Type: multipart/form-data

file: audio file (required)
user_id: user identifier (optional)
```

#### Get Audio File Details
```http
GET /api/audio/{audio_id}
```

#### List Audio Files
```http
GET /api/audio/?user_id=xyz&status=completed&limit=20&offset=0
```

#### Get Transcript
```http
GET /api/audio/{audio_id}/transcript?improved=true
```

#### Download Audio File
```http
GET /api/audio/{audio_id}/download
```

#### Delete Audio File
```http
DELETE /api/audio/{audio_id}
```

### Legacy Endpoints
- Chat endpoints (existing functionality)
- Webhook endpoints (existing functionality)

## Configuration

Key configuration options in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://pegasus:pegasus@localhost/pegasus_db` |
| `AUDIO_STORAGE_PATH` | Path for audio file storage | `./audio_files` |
| `TRANSCRIPTION_ENGINE` | Transcription engine (`whisper` or `deepgram`) | `whisper` |
| `WHISPER_MODEL` | Whisper model size | `base` |
| `DEEPGRAM_API_KEY` | Deepgram API key (if using Deepgram) | `None` |
| `OLLAMA_MODEL` | Ollama model for enhancement | `llama2` |
| `MAX_FILE_SIZE_MB` | Maximum upload size in MB | `100` |

## Processing Pipeline

1. **Upload**: File is uploaded and stored with date-based organization
2. **Transcription**: Audio is transcribed using Whisper or Deepgram
3. **Enhancement**: Transcript is improved using Ollama LLM
4. **Completion**: Final transcript is available via API

## Development

### Running Tests
```bash
python test_audio_api.py  # Audio API tests
pytest                    # Unit tests
```

### Database Migrations
```bash
python scripts/init_db.py                           # Initialize database
alembic upgrade head                                # Apply migrations
alembic revision --autogenerate -m "Description"   # Create migration
```

## Docker Usage

Build and run the Docker image:

```bash
docker build -t pegasus-backend .
docker run -p 8000:8000 pegasus-backend
```

## Troubleshooting

### Common Issues

1. **Database connection errors**: Ensure PostgreSQL is running and credentials are correct
2. **Large file uploads fail**: Check `MAX_UPLOAD_SIZE_BYTES` setting
3. **Whisper transcription slow**: Consider using GPU or smaller model
4. **Ollama enhancement fails**: Ensure Ollama is running and model is available

### Logs
Enable debug logging by setting `LOGLEVEL=DEBUG` in your environment.
