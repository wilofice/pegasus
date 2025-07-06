# Auto-Migration on Startup Guide

## Current Behavior (Updated)

When you run `python main.py`, the app now **automatically handles database setup** based on the `AUTO_MIGRATE_ON_STARTUP` setting.

## Configuration Options

### **Option 1: Auto-Migration Enabled (Default)**
```bash
# In your .env file:
AUTO_MIGRATE_ON_STARTUP=true
```

**What happens on startup:**
1. ✅ **Runs `alembic upgrade head`** automatically
2. ✅ **Applies all pending migrations** 
3. ✅ **Creates tables if database is empty**
4. ✅ **Updates existing tables safely**
5. ✅ **Logs all migration activity**

### **Option 2: Auto-Migration Disabled**
```bash
# In your .env file:
AUTO_MIGRATE_ON_STARTUP=false
```

**What happens on startup:**
1. ✅ **Runs `Base.metadata.create_all()`** only
2. ✅ **Creates missing tables**
3. ❌ **Does NOT update existing tables**
4. ❌ **Does NOT run migrations**

## Startup Flow

```
python main.py
    ↓
Check AUTO_MIGRATE_ON_STARTUP setting
    ↓
┌─ TRUE (default) ──────────────┐   ┌─ FALSE ──────────────────────┐
│ 1. Run alembic upgrade head   │   │ 1. Run create_tables()       │
│ 2. Apply all migrations       │   │ 2. Create missing tables     │
│ 3. Fallback to create_tables  │   │ 3. Skip existing tables      │
│    if alembic fails           │   │                               │
└───────────────────────────────┘   └───────────────────────────────┘
    ↓
App starts successfully
```

## Benefits of Auto-Migration

### ✅ **Development Benefits:**
- **No manual steps** - just run the app
- **Always up-to-date** schema
- **Team synchronization** - everyone gets latest changes
- **Prevents schema drift** issues

### ✅ **Production Benefits:**
- **Automated deployments** handle migrations
- **Zero-downtime** updates (when migrations are compatible)
- **Rollback safety** through migration system
- **Audit trail** of all schema changes

### ✅ **Safety Features:**
- **Fallback mechanism** - if migrations fail, creates tables directly
- **Timeout protection** - migrations timeout after 60 seconds
- **Error logging** - detailed logs for troubleshooting
- **Non-destructive** - migrations only add/modify, never delete data

## When Each Option is Best

### **Use Auto-Migration (TRUE) When:**
- 👥 **Working in a team**
- 🚀 **Production deployments**
- 🔄 **Continuous integration/deployment**
- 📦 **Docker containers**
- 🎯 **You want "it just works" behavior**

### **Use Manual Setup (FALSE) When:**
- 🧪 **Testing/development** with frequent schema changes
- 🔧 **Debugging migration issues**
- 🎛️ **Need precise control** over when migrations run
- 💾 **Database has sensitive production data**

## Troubleshooting

### **Migration Fails on Startup**
```
ERROR: Migration failed: relation "xyz" already exists
```

**Solution 1: Mark current state**
```bash
alembic stamp head
```

**Solution 2: Reset migration tracking**
```bash
# Check what migrations alembic thinks are applied
alembic current

# If empty but tables exist, mark latest migration as applied
alembic stamp 006_conversation_history_tags
```

### **Startup Takes Too Long**
```
WARNING: Could not run migrations: Timeout after 60 seconds
```

**Solutions:**
1. **Increase timeout** in `main.py` (change `timeout=60`)
2. **Run migrations manually** before starting app
3. **Disable auto-migration** temporarily

### **Alembic Not Found**
```
WARNING: Could not run migrations: FileNotFoundError: alembic
```

**Solution:**
```bash
pip install alembic
# or
pip install -r requirements.txt
```

## Best Practices

### **Development Workflow:**
```bash
# 1. Pull latest code
git pull

# 2. Start app (auto-migration handles the rest)
python main.py
```

### **Production Deployment:**
```bash
# Option 1: Let app handle it
AUTO_MIGRATE_ON_STARTUP=true python main.py

# Option 2: Manual control
alembic upgrade head
AUTO_MIGRATE_ON_STARTUP=false python main.py
```

### **Team Collaboration:**
1. **Keep auto-migration enabled** for consistency
2. **Commit migration files** to git
3. **Test migrations locally** before pushing
4. **Use descriptive migration messages**

## Environment Variables

Add to your `.env` file:
```bash
# Database auto-migration (default: true)
AUTO_MIGRATE_ON_STARTUP=true

# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/pegasus
```

## Summary

With the updated setup:
- ✅ **`python main.py` handles everything automatically**
- ✅ **Migrations run on every startup** (by default)
- ✅ **Safe fallback** if migrations fail
- ✅ **Configurable behavior** via environment variable
- ✅ **Production ready** with proper error handling

You can now just run `python main.py` and trust that your database will be properly set up with the latest schema!