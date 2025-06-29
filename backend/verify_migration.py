#!/usr/bin/env python3
"""Verify that the database migration was applied correctly."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

async def verify_migration():
    """Check if the tag and category columns exist in audio_files table."""
    try:
        from core.database import async_session
        from sqlalchemy import text
        
        print("🔍 Verifying database migration...")
        
        async with async_session() as session:
            # Check if the columns exist
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'audio_files' 
                AND column_name IN ('tag', 'category')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            
            if len(columns) == 2:
                print("✅ Migration successful! New columns found:")
                for col in columns:
                    print(f"   📌 {col[0]} ({col[1]}, nullable: {col[2]})")
                
                # Test creating a record with tags
                from models.audio_file import AudioFile, ProcessingStatus
                from repositories.audio_repository import AudioRepository
                
                repo = AudioRepository(session)
                
                # Create test audio file with tag
                test_data = {
                    "filename": "test_migration.m4a",
                    "original_filename": "test.m4a", 
                    "file_path": "/tmp/test_migration.m4a",
                    "file_size_bytes": 1024,
                    "mime_type": "audio/mp4",
                    "user_id": "migration_test",
                    "processing_status": ProcessingStatus.UPLOADED,
                    "tag": "Migration Test",
                    "category": "Testing"
                }
                
                audio_file = await repo.create(test_data)
                print(f"✅ Successfully created test record with tag: '{audio_file.tag}'")
                
                # Clean up test record
                await repo.delete(audio_file.id)
                print("🧹 Cleaned up test record")
                
                return True
                
            elif len(columns) == 1:
                print("⚠️  Partial migration: Only found one column:")
                for col in columns:
                    print(f"   📌 {col[0]} ({col[1]})")
                print("❌ Missing column. Migration may have failed.")
                return False
                
            else:
                print("❌ Migration failed: No tag/category columns found")
                print("   Run the migration first: alembic upgrade head")
                return False
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have all dependencies installed:")
        print("   pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("This could mean:")
        print("  - Database is not running")
        print("  - Database connection settings are wrong") 
        print("  - Migration hasn't been run yet")
        return False

async def show_table_structure():
    """Show the current structure of the audio_files table."""
    try:
        from core.database import async_session
        from sqlalchemy import text
        
        print("\n📋 Current audio_files table structure:")
        print("-" * 60)
        
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'audio_files'
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"  {col[0]:<25} {col[1]:<20} {nullable}{default}")
                
    except Exception as e:
        print(f"❌ Could not show table structure: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify database migration")
    parser.add_argument("--show-structure", action="store_true", 
                       help="Show complete table structure")
    
    args = parser.parse_args()
    
    success = asyncio.run(verify_migration())
    
    if args.show_structure:
        asyncio.run(show_table_structure())
    
    if success:
        print("\n🎉 Database is ready for the new audio tagging features!")
    else:
        print("\n💡 Next steps:")
        print("   1. Install alembic: pip install --break-system-packages alembic")
        print("   2. Run migration: alembic upgrade head")
        print("   3. Verify again: python3 verify_migration.py")
    
    sys.exit(0 if success else 1)