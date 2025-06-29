#!/usr/bin/env python3
"""Debug script for the tags endpoint 422 error."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

async def debug_tags_endpoint():
    """Debug the tags endpoint to identify the 422 error."""
    try:
        from core.database import async_session
        from repositories.audio_repository import AudioRepository
        from sqlalchemy import text, inspect
        
        print("🔍 Debugging /api/audio/tags endpoint...")
        print("-" * 50)
        
        async with async_session() as db:
            # Check if audio_files table exists
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            print(f"📋 Available tables: {tables}")
            
            if 'audio_files' not in tables:
                print("❌ audio_files table doesn't exist!")
                print("   Run: python3 scripts/init_db.py")
                return False
            
            # Check table columns
            columns = [col['name'] for col in inspector.get_columns('audio_files')]
            print(f"📋 audio_files columns: {columns}")
            
            # Check if tag/category columns exist
            has_tag = 'tag' in columns
            has_category = 'category' in columns
            
            print(f"📋 Tag column exists: {'✅' if has_tag else '❌'}")
            print(f"📋 Category column exists: {'✅' if has_category else '❌'}")
            
            if not has_tag or not has_category:
                print("\n❌ Missing tag/category columns!")
                print("   This is the cause of the 422 error.")
                print("   Run the migration: alembic upgrade head")
                print("   Or use: python3 resolve_migration_error.py")
                return False
            
            # Test the repository methods directly
            audio_repo = AudioRepository(db)
            
            print("\n🧪 Testing repository methods...")
            
            try:
                tags = await audio_repo.get_available_tags()
                print(f"✅ get_available_tags(): {tags}")
            except Exception as e:
                print(f"❌ get_available_tags() failed: {e}")
                return False
            
            try:
                categories = await audio_repo.get_available_categories()
                print(f"✅ get_available_categories(): {categories}")
            except Exception as e:
                print(f"❌ get_available_categories() failed: {e}")
                return False
            
            # Test creating an audio file with tags to populate data
            if len(tags) == 0:
                print("\n📝 No tags found, creating test data...")
                try:
                    from models.audio_file import ProcessingStatus
                    test_data = {
                        "filename": "debug_test.m4a",
                        "original_filename": "debug.m4a",
                        "file_path": "/tmp/debug_test.m4a",
                        "file_size_bytes": 1024,
                        "mime_type": "audio/mp4",
                        "user_id": "debug_user",
                        "processing_status": ProcessingStatus.UPLOADED,
                        "tag": "Debug",
                        "category": "Testing"
                    }
                    
                    audio_file = await audio_repo.create(test_data)
                    print(f"✅ Created test audio file with tag: {audio_file.tag}")
                    
                    # Test again
                    tags = await audio_repo.get_available_tags()
                    categories = await audio_repo.get_available_categories()
                    print(f"✅ Tags after test data: {tags}")
                    print(f"✅ Categories after test data: {categories}")
                    
                    # Clean up
                    await audio_repo.delete(audio_file.id)
                    print("🧹 Cleaned up test data")
                    
                except Exception as e:
                    print(f"❌ Test data creation failed: {e}")
                    return False
            
            print("\n🎉 Repository methods work correctly!")
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the backend directory")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Check your database connection and .env settings")
        return False

async def test_endpoint_directly():
    """Test the endpoint directly by calling the function."""
    try:
        from core.database import async_session
        from api.audio_router import get_available_tags
        from schemas.audio import AudioTagsResponse
        
        print("\n🧪 Testing endpoint function directly...")
        
        async with async_session() as db:
            try:
                # Call the endpoint function directly
                result = await get_available_tags(user_id=None, db=db)
                
                print(f"✅ Endpoint function returned: {type(result)}")
                print(f"   Tags: {result.tags}")
                print(f"   Categories: {result.categories}")
                
                # Validate the response model
                if isinstance(result, AudioTagsResponse):
                    print("✅ Response model validation passed")
                    return True
                else:
                    print(f"❌ Invalid response type: {type(result)}")
                    return False
                    
            except Exception as e:
                print(f"❌ Endpoint function failed: {e}")
                print(f"   Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

async def check_migration_state():
    """Check Alembic migration state."""
    try:
        from alembic import command
        from alembic.config import Config
        
        print("\n🔍 Checking Alembic migration state...")
        
        if not Path('alembic.ini').exists():
            print("❌ alembic.ini not found")
            return False
            
        alembic_cfg = Config('alembic.ini')
        
        try:
            current_rev = command.current(alembic_cfg)
            print(f"📍 Current revision: {current_rev or 'None'}")
            
            if not current_rev:
                print("❌ No migration applied!")
                print("   This is likely the cause of the 422 error")
                return False
            elif current_rev == '001':
                print("⚠️  Only base migration applied, tag columns missing")
                print("   Run: alembic upgrade 002")
                return False
            elif current_rev == '002':
                print("✅ All migrations applied")
                return True
            else:
                print(f"⚠️  Unknown revision: {current_rev}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to check revision: {e}")
            return False
            
    except ImportError:
        print("❌ Alembic not available")
        return False
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False

async def main():
    """Main debug function."""
    print("🚨 Debugging 422 Error for /api/audio/tags endpoint")
    print("=" * 60)
    
    # Check migration state first
    migration_ok = await check_migration_state()
    
    # Check database state
    db_ok = await debug_tags_endpoint()
    
    # Test endpoint function
    endpoint_ok = await test_endpoint_directly()
    
    print("\n" + "=" * 60)
    print("🎯 Summary:")
    print(f"   Migration state: {'✅' if migration_ok else '❌'}")
    print(f"   Database state: {'✅' if db_ok else '❌'}")
    print(f"   Endpoint function: {'✅' if endpoint_ok else '❌'}")
    
    if not migration_ok:
        print("\n💡 SOLUTION: Run migration to add tag/category columns")
        print("   python3 resolve_migration_error.py")
        print("   OR")
        print("   alembic stamp 001 && alembic upgrade 002")
    elif not db_ok:
        print("\n💡 SOLUTION: Check database connection and table structure")
    elif not endpoint_ok:
        print("\n💡 SOLUTION: Check server logs for detailed error information")
    else:
        print("\n🎉 Everything looks good! The 422 error might be temporary.")
        print("   Try the request again or check server logs.")
    
    return migration_ok and db_ok and endpoint_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)