# Database Setup Guide for Pegasus

## For Brand New Databases 

You have **three options** for setting up a brand new database:

### **Option 1: Direct Table Creation (Fastest)**
```bash
cd backend
python scripts/init_db.py
```
**✅ Pros:** Fastest, creates all tables with latest schema  
**❌ Cons:** No migration tracking for future updates

### **Option 2: Direct + Alembic Tracking (Recommended)**
```bash
cd backend
python scripts/init_db.py --with-alembic
```
**✅ Pros:** Fast + future migration support  
**✅ Recommended:** Best of both worlds

### **Option 3: Pure Alembic (Production Standard)**
```bash
cd backend
alembic upgrade head
```
**✅ Pros:** Full migration tracking, production standard  
**❌ Cons:** Slower (runs all migrations sequentially)

## For Existing Databases

**Always use Alembic migrations:**
```bash
cd backend
alembic upgrade head
```

This safely upgrades your existing database with all the new features.

## Migration Files: Keep or Delete? 

### **✅ KEEP MIGRATION FILES** - Here's why:

1. **Production Databases**: Existing production DBs need migrations
2. **Team Collaboration**: Other developers may have existing databases  
3. **CI/CD Pipelines**: Automated deployments rely on migrations
4. **Rollback Safety**: Migrations provide safe rollback options
5. **Audit Trail**: Shows database schema evolution over time

### **Migration Files Location:**
```
backend/alembic/versions/
├── 001_create_audio_files_table.py
├── 002_add_audio_tags.py  
├── 003_add_language_column.py
├── 004_add_job_queue_tables.py
├── 005_fix_metadata_column_conflict.py
└── 006_add_conversation_history_and_update_tags.py  ← New
```

## What the Latest Migration (006) Does

### **Creates conversation_history table:**
```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    user_id VARCHAR(255), 
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    timestamp TIMESTAMP,
    metadata JSONB
);
```

### **Adds PENDING_REVIEW status:**
- Allows audio processing to pause for user review
- New workflow: `UPLOADED` → `TRANSCRIBING` → `PENDING_REVIEW` → `PENDING_PROCESSING` → `COMPLETED`

### **Converts tags to array:**
- Changes `audio_files.tag` (single string) to `audio_files.tags` (array)
- Safely migrates existing data
- Enables multiple tags per audio file

## Database Setup Commands Reference

### **New Database Setup**
```bash
# Option 1: Fast setup
python scripts/init_db.py

# Option 2: Fast + migration tracking (RECOMMENDED)
python scripts/init_db.py --with-alembic

# Option 3: Pure migration approach
alembic upgrade head
```

### **Development Reset** 
```bash
# ⚠️ DANGEROUS: Deletes all data!
python scripts/init_db.py --drop
```

### **Existing Database Upgrade**
```bash
# Safe upgrade for existing databases
alembic upgrade head
```

### **Check Migration Status**
```bash
# See current migration version
alembic current

# See migration history  
alembic history -v

# See pending migrations
alembic show head
```

### **Testing Database Setup**
```bash
# Test that all tables were created correctly
python test_db_init.py
```

## Troubleshooting

### **"Table already exists" Error**
```bash
# Check what migrations are applied
alembic current

# If tables exist but no migrations are marked:
alembic stamp head
```

### **"Migration not found" Error**
```bash
# Make sure you're in the backend directory
cd backend
alembic upgrade head
```

### **Database Connection Issues**
Check your `.env` file has correct database settings:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/pegasus
```

## Recommendation for Your Setup

For a **brand new database**, I recommend:

```bash
cd backend
python scripts/init_db.py --with-alembic
```

This gives you:
- ✅ Fast table creation with current schema
- ✅ Migration tracking for future updates  
- ✅ Full compatibility with team workflows
- ✅ Production deployment readiness

**Keep all migration files** - they're essential for production deployments and team collaboration.