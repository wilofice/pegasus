#!/usr/bin/env python3
"""
Resolve the specific migration error where 'processingstatus' enum already exists.

This script handles the situation where:
1. init_db.py was run first (creating tables and enums)
2. Alembic migration is attempted but fails because enum already exists
3. We need to sync Alembic state with actual database state
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path  
sys.path.append(str(Path(__file__).parent))

async def check_database_state():
    """Check what actually exists in the database."""
    try:
        from core.database import async_session
        from sqlalchemy import text
        
        print("🔍 Checking actual database state...")
        
        async with async_session() as session:
            # Check if audio_files table exists
            result = await session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'audio_files'
            """))
            table_exists = result.fetchone() is not None
            
            # Check if processingstatus enum exists
            result = await session.execute(text("""
                SELECT typname FROM pg_type 
                WHERE typname = 'processingstatus'
            """))
            enum_exists = result.fetchone() is not None
            
            # Check what columns exist in audio_files
            columns = []
            indexes = []
            if table_exists:
                result = await session.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'audio_files'
                    ORDER BY ordinal_position
                """))
                columns = [row[0] for row in result.fetchall()]
                
                # Check indexes
                result = await session.execute(text("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'audio_files'
                """))
                indexes = [row[0] for row in result.fetchall()]
            
            return {
                'table_exists': table_exists,
                'enum_exists': enum_exists, 
                'columns': columns,
                'indexes': indexes,
                'has_tag_columns': 'tag' in columns and 'category' in columns
            }
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return None

def get_alembic_state():
    """Check current Alembic migration state."""
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        if not Path('alembic.ini').exists():
            return None, "alembic.ini not found"
            
        alembic_cfg = Config('alembic.ini')
        
        # Get current revision
        try:
            current_rev = command.current(alembic_cfg)
        except Exception as e:
            current_rev = None
            
        # Get available revisions
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        revisions = [rev.revision for rev in script_dir.walk_revisions()]
        
        return {
            'current_revision': current_rev,
            'available_revisions': revisions
        }, None
        
    except Exception as e:
        return None, str(e)

async def fix_migration_state():
    """Fix the migration state to match database reality."""
    print("🛠️  Migration Error Resolution Tool")
    print("=" * 50)
    
    # Check database state
    db_state = await check_database_state()
    if not db_state:
        print("❌ Could not check database state")
        return False
        
    print("📋 Database State:")
    print(f"   audio_files table: {'✅' if db_state['table_exists'] else '❌'}")
    print(f"   processingstatus enum: {'✅' if db_state['enum_exists'] else '❌'}")
    print(f"   tag/category columns: {'✅' if db_state['has_tag_columns'] else '❌'}")
    print(f"   total columns: {len(db_state['columns'])}")
    
    # Check Alembic state
    alembic_state, error = get_alembic_state()
    if not alembic_state:
        print(f"❌ Could not check Alembic state: {error}")
        return False
        
    print("\n📋 Alembic State:")
    print(f"   current revision: {alembic_state['current_revision'] or 'None'}")
    print(f"   available revisions: {alembic_state['available_revisions']}")
    
    try:
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config('alembic.ini')
        
        # Determine what to do based on current state
        print("\n🔧 Determining fix strategy...")
        
        if db_state['table_exists'] and db_state['enum_exists']:
            if not alembic_state['current_revision']:
                # Database exists but Alembic doesn't know about it
                print("📌 Strategy: Mark database as migration 001")
                command.stamp(alembic_cfg, '001')
                print("✅ Marked database as migration 001")
                
            if not db_state['has_tag_columns']:
                # Need to add tag columns
                print("📌 Strategy: Run migration 002 to add tag columns")
                command.upgrade(alembic_cfg, '002')
                print("✅ Added tag/category columns")
            else:
                # Tag columns already exist
                print("📌 Strategy: Mark as migration 002 (columns already exist)")
                command.stamp(alembic_cfg, '002')
                print("✅ Marked database as migration 002")
                
        else:
            print("❌ Database is not in expected state")
            print("   Please run init_db.py first")
            return False
            
        # Final verification
        final_rev = command.current(alembic_cfg)
        print(f"\n🎉 Migration state fixed!")
        print(f"   Final revision: {final_rev}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix migration state: {e}")
        return False

async def main():
    """Main function."""
    print("Resolving Alembic migration error: 'processingstatus already exists'\n")
    
    success = await fix_migration_state()
    
    if success:
        print("\n✅ Problem resolved!")
        print("\nNext steps:")
        print("  1. Start your API: python3 main.py")
        print("  2. Test upload: python3 test_upload_endpoint.py")
        print("  3. Verify database: python3 verify_migration.py")
        
        # Offer to run verification
        try:
            run_verify = input("\nRun verification now? (y/n): ").lower().strip()
            if run_verify == 'y':
                print("\n" + "="*50)
                from subprocess import run
                result = run([sys.executable, 'verify_migration.py'], capture_output=True, text=True)
                print(result.stdout)
                if result.stderr:
                    print("Errors:", result.stderr)
        except KeyboardInterrupt:
            print("\nSkipping verification.")
            
    else:
        print("\n❌ Could not resolve the migration error automatically.")
        print("\nManual resolution steps:")
        print("  1. Check that PostgreSQL is running")
        print("  2. Verify database connection in .env")
        print("  3. Ensure init_db.py was run successfully")
        print("  4. Try running: alembic stamp 001")
        print("  5. Then run: alembic upgrade 002")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)