# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Pegasus is a multi-component AI-powered conversational assistant system with:
- **Flutter mobile app** (`/pegasus/`) - Cross-platform app with voice capabilities
- **FastAPI backend** (`/backend/`) - REST API server orchestrating conversations
- **Data pipeline** (`/data_pipeline/`) - Processes documents and audio for vector storage

## Essential Commands

### Flutter App (`/pegasus/`)
```bash
cd pegasus
flutter pub get              # Install dependencies
flutter analyze              # Run static analysis
flutter test                 # Run all tests
flutter test test/[file]     # Run specific test file
flutter run                  # Run app in debug mode
flutter build [platform]     # Build for specific platform
```

### Backend (`/backend/`)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py               # Run server locally
pytest                       # Run all tests
pytest tests/[file]          # Run specific test file

# Docker
docker build -t pegasus-backend .
docker run -p 8000:8000 pegasus-backend
```

### Data Pipeline (`/data_pipeline/`)
```bash
cd data_pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python pipeline.py           # Run the pipeline
```

## Architecture & Key Components

### System Flow
1. **Mobile App** → sends chat requests to → **Backend API** (port 8000)
2. **Data Pipeline** → monitors `source_data/` folder → processes files → stores in **ChromaDB**
3. **Backend** → queries ChromaDB for context → calls external LLM services → returns responses

### Flutter App Structure
- Uses Riverpod for state management
- Firebase Messaging for push notifications
- Speech-to-text and TTS capabilities via `speech_to_text` and `flutter_tts` packages
- Main chat interface implementation in `lib/` directory

### Backend Architecture
- FastAPI framework with async support
- Endpoints: `/chat` and `/webhook` 
- Includes proactive analysis engine
- Tests located in `/backend/tests/`

### Data Pipeline Components
- **Whisper** for audio transcription
- **ChromaDB** for vector storage
- **Sentence Transformers** for embeddings
- Monitors `source_data/` directory for new files
- Processes audio, text, and email files
- Sends completion webhooks after processing

## Key Configuration Files

- **Flutter**: `pegasus/pubspec.yaml`, `pegasus/analysis_options.yaml`
- **Backend**: `backend/requirements.txt`, `backend/Dockerfile`
- **Pipeline**: `data_pipeline/requirements.txt`
- **Firebase**: `pegasus/android/app/google-services.json`, `pegasus/ios/Runner/GoogleService-Info.plist`

## Development Notes

- Flutter app requires Flutter SDK 3.7.2+
- Backend and pipeline require Python 3.9+
- Pipeline requires `ffmpeg` for audio processing
- Task documentation available in `/tasks/` directory (French)