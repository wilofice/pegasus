# MIME Type Fix for Audio Upload

## Problem
The backend was receiving "application/octet-stream" as the MIME type for uploaded audio files instead of proper audio MIME types (like "audio/mp4", "audio/mpeg", etc.), causing the API to return 400 Bad Request errors.

## Root Cause
Flutter's Dio/MultipartFile wasn't automatically detecting the correct MIME type for the uploaded audio files, defaulting to the generic "application/octet-stream" type.

## Solution

### Frontend Changes (Flutter)

1. **Updated API Client** (`/pegasus/lib/api/pegasus_api_client.dart`):
   - Added `http_parser` import for MediaType support
   - Created `_getMimeTypeFromFileName()` helper method to map file extensions to MIME types:
     - `.m4a` → `audio/mp4`
     - `.mp3` → `audio/mpeg` 
     - `.wav` → `audio/wav`
     - `.ogg` → `audio/ogg`
     - `.aac` → `audio/aac`
     - `.flac` → `audio/flac`
     - `.webm` → `audio/webm`
   - Updated `MultipartFile.fromFile()` to explicitly set `contentType: MediaType.parse(mimeType)`
   - Added default `user_id` parameter to upload request

2. **Updated Dependencies** (`/pegasus/pubspec.yaml`):
   - Added `http_parser: ^4.0.2` dependency

### Backend Changes (Python)

1. **Enhanced MIME Type Validation** (`/backend/api/audio_router.py`):
   - Added `application/octet-stream` to `ALLOWED_MIME_TYPES` as fallback
   - Added `audio/flac` to supported MIME types
   - Added `.flac` to `ALLOWED_EXTENSIONS`
   - Improved validation logic to be more lenient:
     - Prioritizes file extension validation over MIME type
     - Logs warning for generic MIME types but allows upload to continue
     - Only rejects if both MIME type and extension are invalid

2. **Database Migration** (`/backend/alembic/versions/002_add_audio_tags.py`):
   - Added `tag` and `category` columns to `audio_files` table
   - Created appropriate indexes for efficient querying

## Testing

Created test script (`/backend/test_upload_endpoint.py`) to verify:
- Valid audio files with correct MIME types
- Valid audio files with generic MIME types (fallback scenario)
- Invalid file types (should be rejected)

## Usage

### Frontend
```dart
// The API client now automatically sets correct MIME types
final result = await _apiClient.uploadAudioFile(File(audioFilePath));
```

### Backend
```bash
# Test the upload endpoint
cd backend
python3 test_upload_endpoint.py [base_url]

# Run database migration (if needed)
# pip install alembic
# python3 -c "from alembic import command; from alembic.config import Config; command.upgrade(Config('alembic.ini'), 'head')"
```

## Result
- ✅ Audio files now upload successfully with proper MIME type detection
- ✅ Fallback handling for cases where MIME type detection fails
- ✅ Better error messages for truly invalid file types
- ✅ Maintains security by validating file extensions regardless of MIME type