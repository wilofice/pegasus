# Alembic Database Migration Guide

## When to Run Migrations

**🔄 Run migrations when:**
- You see new `.py` files in `/backend/alembic/versions/` directory
- After pulling code updates that include database schema changes
- Before starting the API server if there are pending migrations
- You get database-related errors about missing columns/tables

**⚠️ In your case:** You need to run migration `002_add_audio_tags.py` to add `tag` and `category` columns.

## Setup (First Time Only)

### Option 1: Virtual Environment (Recommended)
```bash
cd /Users/galahassa/Dev/pegasus/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Option 2: System Installation (If you're okay with it)
```bash
pip install --break-system-packages alembic
```

### Option 3: Using pipx
```bash
brew install pipx
pipx install alembic
```

## Running Migrations

### Check Current Status
```bash
cd /Users/galahassa/Dev/pegasus/backend

# Check what migrations exist
alembic history

# Check current database revision
alembic current
```

### Run All Pending Migrations
```bash
# Apply all pending migrations to latest (head)
alembic upgrade head
```

### Run Specific Migration
```bash
# Apply specific migration by revision ID
alembic upgrade 002  # For the tags migration
```

### Alternative: Use the Helper Script
```bash
# Run all migrations
python3 run_migrations.py

# Check migration status
python3 run_migrations.py status

# Create new migration (for future use)
python3 run_migrations.py create --message "Add new feature"
```

## Expected Output

When you run the migration successfully, you should see:
```
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, Add tag and category columns to audio_files table
```

## Troubleshooting

### Database Connection Issues
If you get connection errors:
1. Make sure PostgreSQL is running
2. Check your `.env` file for correct database credentials
3. Verify the `DATABASE_URL` in your configuration

### Migration Already Applied
If you get "Target database is not up to date":
```bash
# Check current revision
alembic current

# If it shows 002, the migration is already applied
# You can safely start your API server
```

### Permission Issues
If you get permission errors:
```bash
# Make sure you have write permissions to the database
# Check if your database user has CREATE/ALTER permissions
```

## Migration Files Explained

- `001_create_audio_files_table.py` - Creates the initial audio_files table
- `002_add_audio_tags.py` - Adds tag and category columns (THIS IS THE ONE YOU NEED)

## After Running Migrations

1. **Start your API server**:
   ```bash
   python3 main.py
   ```

2. **Test the upload endpoint**:
   ```bash
   python3 test_upload_endpoint.py
   ```

3. **Verify the new columns exist**:
   Connect to your database and run:
   ```sql
   \d audio_files  -- PostgreSQL
   ```
   You should see `tag` and `category` columns.

## Quick Command Summary

```bash
# Navigate to backend directory
cd /Users/galahassa/Dev/pegasus/backend

# Install dependencies (if not done)
pip install --break-system-packages alembic

# Run migration
alembic upgrade head

# Start API server
python3 main.py
```

**That's it!** Your database will now have the `tag` and `category` columns needed for the new audio tagging functionality.