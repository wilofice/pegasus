#!/usr/bin/env python3
"""Fix Alembic migration state when database was created with init_db.py."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def fix_migration_state():
    """Mark the current database state as migration 001 and run pending migrations."""
    try:
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect, text
        from core.database import async_session
        import asyncio
        
        if not Path('alembic.ini').exists():
            print("❌ alembic.ini not found")
            return False
            
        alembic_cfg = Config('alembic.ini')
        
        print("🔍 Checking current database state...")
        
        # Check if table exists and what columns it has
        async def check_db_state():
            async with async_session() as session:
                try:
                    # Check if audio_files table exists
                    result = await session.execute(text("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'audio_files'
                    """))
                    table_exists = result.fetchone() is not None
                    
                    if table_exists:
                        # Check what columns exist
                        result = await session.execute(text("""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name = 'audio_files' 
                            AND column_name IN ('tag', 'category')
                        """))
                        tag_columns = [row[0] for row in result.fetchall()]
                        
                        return table_exists, tag_columns
                    else:
                        return False, []
                except Exception as e:
                    print(f"❌ Database check failed: {e}")
                    return None, []
        
        table_exists, tag_columns = asyncio.run(check_db_state())
        
        if table_exists is None:
            print("❌ Could not check database state")
            return False
            
        print(f"📋 Database state:")
        print(f"   audio_files table exists: {table_exists}")
        print(f"   tag/category columns: {tag_columns}")
        
        if table_exists:
            try:
                # Check current Alembic revision
                current_rev = command.current(alembic_cfg)
                print(f"📍 Current Alembic revision: {current_rev or 'None'}")
                
                if not current_rev:
                    # Mark the database as being at revision 001
                    print("🔧 Marking database as migration 001 (base state)...")
                    command.stamp(alembic_cfg, '001')
                    print("✅ Database marked as migration 001")
                
                # Now check if we need migration 002 (tags)
                if len(tag_columns) == 0:
                    print("🔄 Running migration 002 to add tag/category columns...")
                    command.upgrade(alembic_cfg, '002')
                    print("✅ Migration 002 completed successfully!")
                elif len(tag_columns) == 2:
                    print("✅ Tag columns already exist, marking as migration 002...")
                    command.stamp(alembic_cfg, '002')
                else:
                    print("⚠️  Partial tag columns found. Please check database manually.")
                    return False
                    
            except Exception as e:
                print(f"❌ Alembic operation failed: {e}")
                return False
                
        else:
            print("❌ audio_files table doesn't exist. Run init_db.py first.")
            return False
            
        # Final verification
        current_rev = command.current(alembic_cfg)
        print(f"🎉 Final state - Alembic revision: {current_rev}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Alembic is installed: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def show_migration_info():
    """Show information about the migration fix."""
    print("🛠️  Migration State Fix Tool")
    print("=" * 50)
    print()
    print("This script fixes the situation where:")
    print("1. You ran init_db.py to create the database")
    print("2. Alembic doesn't know the current migration state")
    print("3. Trying to run migrations fails with 'already exists' errors")
    print()
    print("What this script does:")
    print("✅ Checks current database state") 
    print("✅ Marks existing tables as migration 001")
    print("✅ Runs pending migration 002 (adds tag/category columns)")
    print("✅ Updates Alembic revision tracking")
    print()

if __name__ == "__main__":
    show_migration_info()
    
    print("🚀 Starting migration state fix...")
    print()
    
    success = fix_migration_state()
    
    if success:
        print()
        print("🎉 Migration state fixed successfully!")
        print("Your database is now ready with:")
        print("  ✅ audio_files table (from init_db.py)")
        print("  ✅ tag and category columns (from migration 002)")
        print("  ✅ Proper Alembic revision tracking")
        print()
        print("You can now:")
        print("  - Start your API server: python3 main.py")
        print("  - Test uploads: python3 test_upload_endpoint.py")
        print("  - Verify migration: python3 verify_migration.py")
    else:
        print()
        print("❌ Migration state fix failed!")
        print("Manual steps to resolve:")
        print("  1. Check database connection")
        print("  2. Ensure init_db.py was run successfully")
        print("  3. Install Alembic: pip install alembic")
        print("  4. Check database permissions")
    
    sys.exit(0 if success else 1)