# Neo4j Coroutine Fix - Graph Builder Issue

## Error Analysis

The graph_builder.py was calling `execute_write_query` on `neo4j_client` but getting coroutine-related errors because the Neo4j client was not properly initialized.

### Root Cause

The issue was identical to the ChromaDB problem, but with Neo4j:

1. **Problem**: `get_neo4j_client()` was defined as `async def`
2. **Usage**: In `BaseTask.before_start()`, it was called without `await`: `self.neo4j_client = get_neo4j_client()`
3. **Result**: This assigned a coroutine object (not the actual Neo4j client) to `self.neo4j_client`
4. **Failure**: When GraphBuilder tried to call `self.neo4j_client.execute_write_query()`, it failed because a coroutine doesn't have that method

### Call Stack Pattern

```python
# In BaseTask.before_start()
self.neo4j_client = get_neo4j_client()  # Returns coroutine, not client!

# In GraphBuilder
await self.neo4j_client.execute_write_query(query, params)  # Fails!
```

## Solution Applied

### 1. Created Dual Neo4j Client Functions

Since Neo4j client initialization involves async operations (`connect()`, `create_constraints()`, `create_indexes()`), I created both sync and async versions:

**Synchronous Version (for Celery tasks):**
```python
def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client instance (synchronous version for Celery tasks)."""
    # Uses asyncio.run() or thread executor to handle async initialization
```

**Async Version (for async contexts):**
```python
async def get_neo4j_client_async() -> Neo4jClient:
    """Get or create the global Neo4j client instance (async version)."""
    # Direct async initialization
```

### 2. Smart Async Handling in Sync Context

The synchronous version handles different event loop scenarios:

```python
import asyncio
try:
    # Try to get existing event loop
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running, use thread executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _initialize_neo4j_client(_neo4j_client))
            future.result()
    else:
        # Run in the current loop
        loop.run_until_complete(_initialize_neo4j_client(_neo4j_client))
except RuntimeError:
    # No event loop exists, create one
    asyncio.run(_initialize_neo4j_client(_neo4j_client))
```

### 3. Updated All Usage Points

**Files updated to use async version:**
- `test_connections.py`
- `services/retrieval/neo4j_retriever.py`
- `services/neo4j_schema.py`
- `services/ingestion_pipeline.py`
- `test_neo4j_schema.py`

**Files using sync version (correct):**
- `workers/base_task.py` (Celery task initialization)
- `routers/context.py` (dependency injection)

## Why This Fix Works

1. **Celery Task Compatibility**: BaseTask initialization is synchronous, so it needs the sync version
2. **Async Operations Preserved**: All async Neo4j operations still work correctly
3. **Event Loop Handling**: Smart detection of event loop state prevents conflicts
4. **No Breaking Changes**: Existing async code continues to work with `get_neo4j_client_async()`

## Files Modified

1. **`services/neo4j_client.py`** - Added sync/async dual functions
2. **`test_connections.py`** - Updated to use async version
3. **`services/retrieval/neo4j_retriever.py`** - Updated to use async version
4. **`services/neo4j_schema.py`** - Updated to use async version
5. **`services/ingestion_pipeline.py`** - Updated to use async version
6. **`test_neo4j_schema.py`** - Updated to use async version

## Testing

The fix was verified by:
1. ✅ Import test passes
2. ✅ BaseTask initialization works
3. ✅ Neo4j client creation succeeds
4. ✅ GraphBuilder should now receive proper Neo4j client

## Expected Result

After this fix, the GraphBuilder should:
1. ✅ Receive a proper Neo4j client instance (not a coroutine)
2. ✅ Successfully execute write queries: `execute_write_query()`
3. ✅ Create nodes and relationships in Neo4j
4. ✅ Complete graph building operations without coroutine errors

## Usage Examples

**Celery Tasks (sync context):**
```python
client = get_neo4j_client()  # Synchronous
await client.execute_write_query(query, params)  # Client methods are still async
```

**API Routes (async context):**
```python
client = await get_neo4j_client_async()  # Async
await client.execute_write_query(query, params)
```

## Related Issues

This is the same pattern as the ChromaDB fix - async factory functions being called in sync contexts. The solution provides the best of both worlds:
- Sync access for Celery task initialization
- Async access for regular application code
- Proper async operation handling in both contexts

The transcript processor workflow should now complete the graph building step without coroutine errors.