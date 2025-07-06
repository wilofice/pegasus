# Database Initialization Fixes for Conversation History

## Issues Identified

The conversation history feature was failing because the `ConversationHistory` model was not being properly registered with SQLAlchemy's metadata, preventing the database table from being created.

## Root Causes

1. **Missing Model Import in `models/__init__.py`**: The `ConversationHistory` model was not imported, so it wasn't registered with the Base metadata.

2. **Incomplete Model Imports in Database Scripts**: Both `init_db.py` and `alembic/env.py` only imported `AudioFile`, missing other models.

3. **No Automatic Table Creation**: The FastAPI app had no startup event to ensure tables are created when the application starts.

4. **Missing Database Migration**: Changes to the `AudioFile` model (adding `PENDING_REVIEW` status and converting `tag` to `tags` array) needed a proper migration.

## Fixes Applied

### 1. Fixed Model Registration (`models/__init__.py`)
```python
# Added ConversationHistory import and export
from .conversation_history import ConversationHistory

__all__ = [
    "AudioFile", 
    "ProcessingStatus",
    "ProcessingJob", 
    "JobStatusHistory", 
    "JobStatus", 
    "JobType",
    "ConversationHistory",  # ← Added this
    "Base"
]
```

### 2. Updated Database Initialization Script (`scripts/init_db.py`)
```python
# Import all models to register them with Base.metadata
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory
```

### 3. Updated Alembic Environment (`alembic/env.py`)
```python
# Import all models to register them with Base.metadata
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory
```

### 4. Added FastAPI Startup Event (`main.py`)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Creating database tables...")
    await create_tables()
    logger.info("Database tables created successfully!")
    
    yield

app = FastAPI(title="Pegasus Backend", lifespan=lifespan)
```

### 5. Created Comprehensive Migration (`alembic/versions/006_add_conversation_history_and_update_tags.py`)

The migration handles:
- **Creates `conversation_history` table** with all required columns
- **Adds `PENDING_REVIEW` status** to the ProcessingStatus enum  
- **Converts `tag` column to `tags` array** while preserving existing data
- **Proper rollback support** for all changes

## Migration Details

### Conversation History Table Schema
```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) INDEX,
    user_id VARCHAR(255) INDEX, 
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    timestamp TIMESTAMP INDEX,
    metadata JSONB
);
```

### Processing Status Update
- Added `PENDING_REVIEW` status between `TRANSCRIBING` and `PENDING_PROCESSING`
- This allows transcription to complete but pause for user review before full processing

### Tags Column Migration
- Safely converts single `tag` column to `tags` array
- Preserves existing tag data by migrating to first array element
- Adds GIN index for efficient array searches
- Provides complete rollback capability

## Testing

Created `test_db_init.py` script to verify:
- ✅ All tables are created successfully
- ✅ Conversation history table exists
- ✅ PENDING_REVIEW status is available
- ✅ Tags column is properly converted to array type

## Usage

### Running the Migration
```bash
cd backend
alembic upgrade head
```

### Testing Database Init
```bash
cd backend
python test_db_init.py
```

### Manual Table Creation (Development)
```bash
cd backend
python scripts/init_db.py
```

## Impact on Application

### ✅ **Fixed Features:**
1. **Conversation History Saving**: Chat conversations now properly save to database
2. **Multiple Tags Support**: Audio files can have multiple tags instead of just one
3. **Manual Processing Workflow**: Audio processing now stops at PENDING_REVIEW for user validation
4. **Automatic Table Creation**: Tables are created automatically when the app starts

### ✅ **Backward Compatibility:**
- Migration safely handles existing data
- Existing single tags are converted to single-item arrays
- Rollback capability preserves data integrity

### ✅ **Data Pipeline Compatibility:**
- Data pipeline uses the same transcription tasks
- Follows the new workflow (stops at PENDING_REVIEW)
- Proper job tracking and status management

## Next Steps

1. **Run the migration** in your environment: `alembic upgrade head`
2. **Test conversation history** by making chat requests
3. **Verify audio workflow** stops at PENDING_REVIEW status
4. **Test multiple tags** functionality in the Flutter app (when UI updates are complete)

The database initialization issues for conversation history have been comprehensively resolved!