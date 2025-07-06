# Celery Task Error Fix

## Error Analysis

The Celery task was failing with the following error:
```
AttributeError: 'coroutine' object has no attribute 'add_documents'
```

### Root Cause

The issue was in the `get_chromadb_client()` function in `services/vector_db_client.py`:

1. **Problem**: The function was defined as `async def get_chromadb_client()` 
2. **Usage**: In `workers/base_task.py`, it was called without `await`: `self.chromadb_client = get_chromadb_client()`
3. **Result**: This assigned a coroutine object (not the actual client) to `self.chromadb_client`
4. **Failure**: When the task tried to call `self.chromadb_client.add_documents()`, it failed because coroutines don't have that method

### Call Stack

```
File "transcript_processor.py", line 108, in _process_transcript_async
    await self.chromadb_client.add_documents(
AttributeError: 'coroutine' object has no attribute 'add_documents'
```

## Solution Applied

### 1. Fixed `get_chromadb_client()` Function

**Before:**
```python
async def get_chromadb_client() -> ChromaDBClient:
    """Get or create the global ChromaDB client instance."""
    # ... implementation
```

**After:**
```python
def get_chromadb_client() -> ChromaDBClient:
    """Get or create the global ChromaDB client instance."""
    # ... implementation
```

### 2. Updated Test Connection Script

**Before:**
```python
client = await get_chromadb_client()
```

**After:**
```python
client = get_chromadb_client()
```

## Why This Fix Works

1. **Synchronous Initialization**: Celery task initialization happens in synchronous context (`before_start`)
2. **Async Methods**: The ChromaDB client itself still supports async operations via `async def add_documents()`, etc.
3. **No Breaking Changes**: All existing async usage of the client methods remains unchanged
4. **Consistency**: The function now matches how it's actually used throughout the codebase

## Files Modified

1. `services/vector_db_client.py` - Removed `async` from `get_chromadb_client()`
2. `test_connections.py` - Removed `await` from `get_chromadb_client()` call

## Testing

The fix was verified by:
1. ✅ Import test passes
2. ✅ BaseTask initialization works
3. ✅ ChromaDB client creation succeeds

## Additional Notes

### Configuration Issues Also Present

The error log also showed warnings about missing spaCy models:
```
WARNING - Could not load spaCy model for en, using blank model
WARNING - Could not load spaCy model for fr, using blank model
```

These warnings don't cause failures but may affect entity extraction quality. To fix:
```bash
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
```

### Configuration Values

Current configuration shows:
- `OLLAMA_BASE_URL=http://localhost:11435` 
- `OLLAMA_MODEL=llama2`

These were intentionally set by the user and left unchanged.

## Expected Result

After this fix, the Celery task should:
1. ✅ Initialize ChromaDB client successfully
2. ✅ Process transcript chunks
3. ✅ Add documents to ChromaDB
4. ✅ Complete without the coroutine error

The transcript processing workflow should now work end-to-end.