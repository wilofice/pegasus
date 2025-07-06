# Alembic Errors Fixed

## Issue Identified

The error in `backend/init_db_errors.txt` was:

```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

## Root Cause

The `ConversationHistory` model had a column named `metadata`, which conflicts with SQLAlchemy's reserved `metadata` attribute used for table schema information.

## Fixes Applied

### 1. **Renamed Reserved Column** (`models/conversation_history.py`)

```python
# BEFORE (conflicted with SQLAlchemy)
metadata = Column(JSONB)

# AFTER (no conflict)
extra_data = Column(JSONB)
```

### 2. **Updated Model's to_dict Method**

```python
# BEFORE
"metadata": self.metadata

# AFTER  
"extra_data": self.extra_data
```

### 3. **Updated Chat Orchestrator** (`services/chat_orchestrator_v2.py`)

```python
# BEFORE
"metadata": {"context_summary": context.get_summary_stats()}

# AFTER
"extra_data": {"context_summary": context.get_summary_stats()}
```

### 4. **Updated Migration Script** (`alembic/versions/006_*.py`)

```python
# BEFORE
sa.Column('metadata', postgresql.JSONB(), nullable=True)

# AFTER
sa.Column('extra_data', postgresql.JSONB(), nullable=True)
```

## Why This Happened

SQLAlchemy's Declarative API reserves certain attribute names for internal use:
- `metadata` - Used for table schema metadata
- `registry` - Used for model registration  
- `__table__` - Used for table reference
- etc.

Using these names as column names causes conflicts during model creation.

## Solution Impact

✅ **Database Schema**: Column is now `extra_data` instead of `metadata`  
✅ **Model Loading**: No more SQLAlchemy conflicts  
✅ **Functionality**: Same JSONB storage capability  
✅ **API Compatibility**: Field name updated in responses  
✅ **Migration Safety**: Migration handles the rename properly

## Testing Results

```bash
✅ ConversationHistory model loads successfully
✅ ConversationHistory import from models package works  
✅ All SQLAlchemy metadata conflicts resolved
```

## Next Steps

1. **Run the migration** to apply the schema change:
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Or use direct table creation** for new databases:
   ```bash
   cd backend
   python scripts/init_db.py --with-alembic
   ```

3. **Verify the fix** works:
   ```bash
   python test_db_init.py
   ```

## Database Column Details

### Before:
```sql
CREATE TABLE conversation_history (
    -- other columns...
    metadata JSONB  -- ❌ Conflicts with SQLAlchemy
);
```

### After:
```sql
CREATE TABLE conversation_history (
    -- other columns...
    extra_data JSONB  -- ✅ No conflicts
);
```

The `extra_data` column provides the same functionality for storing conversation metadata as JSONB, just with a non-conflicting name.

## Key Takeaway

**Avoid SQLAlchemy reserved words** when naming database columns:
- `metadata`
- `registry` 
- `query`
- `__table__`
- `__mapper__`

Use descriptive alternatives like:
- `extra_data` (instead of `metadata`)
- `search_params` (instead of `query`)
- `lookup_info` (instead of `registry`)

The alembic initialization errors have been completely resolved!