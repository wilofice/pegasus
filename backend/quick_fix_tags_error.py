#!/usr/bin/env python3
"""Quick fix for 422 tags endpoint error - add missing columns."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

async def check_and_fix_tags_columns():
    """Check if tag/category columns exist and add them if missing."""
    try:
        from core.database import async_session
        from sqlalchemy import text
        
        print("🔍 Quick Fix: Checking for missing tag/category columns...")
        print("-" * 55)
        
        async with async_session() as session:
            # Check if columns exist
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'audio_files' 
                AND column_name IN ('tag', 'category')
                ORDER BY column_name;
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            print(f"📋 Existing tag columns: {existing_columns}")
            
            needs_tag = 'tag' not in existing_columns
            needs_category = 'category' not in existing_columns
            
            if not needs_tag and not needs_category:
                print("✅ Both tag and category columns already exist!")
                return True
            
            print(f"⚠️  Missing columns: tag={needs_tag}, category={needs_category}")
            print("\n🔧 Adding missing columns...")
            
            # Add missing columns
            if needs_tag:
                await session.execute(text("""
                    ALTER TABLE audio_files 
                    ADD COLUMN tag VARCHAR(100);
                """))
                print("✅ Added 'tag' column")
            
            if needs_category:
                await session.execute(text("""
                    ALTER TABLE audio_files 
                    ADD COLUMN category VARCHAR(100);
                """))
                print("✅ Added 'category' column")
            
            # Create indexes
            if needs_tag:
                try:
                    await session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_audio_files_tag 
                        ON audio_files (tag);
                    """))
                    print("✅ Created tag index")
                except Exception as e:
                    print(f"⚠️  Tag index creation failed (might already exist): {e}")
            
            if needs_category:
                try:
                    await session.execute(text("""
                        CREATE INDEX IF NOT EXISTS ix_audio_files_category 
                        ON audio_files (category);
                    """))
                    print("✅ Created category index")
                except Exception as e:
                    print(f"⚠️  Category index creation failed (might already exist): {e}")
            
            # Commit changes
            await session.commit()
            print("✅ Changes committed to database")
            
            # Verify the fix
            print("\n🧪 Testing the tags endpoint...")
            from repositories.audio_repository import AudioRepository
            
            audio_repo = AudioRepository(session)
            tags = await audio_repo.get_available_tags()
            categories = await audio_repo.get_available_categories()
            
            print(f"✅ Tags query successful: {tags}")
            print(f"✅ Categories query successful: {categories}")
            
            print("\n🎉 Fix applied successfully!")
            print("The /api/audio/tags endpoint should now work.")
            
            return True
            
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tags_endpoint():
    """Test the tags endpoint after the fix."""
    try:
        from core.database import async_session
        from api.audio_router import get_available_tags
        
        print("\n🧪 Testing tags endpoint function...")
        
        async with async_session() as db:
            result = await get_available_tags(user_id=None, db=db)
            print(f"✅ Endpoint test successful!")
            print(f"   Response type: {type(result)}")
            print(f"   Tags: {result.tags}")
            print(f"   Categories: {result.categories}")
            return True
            
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        return False

async def main():
    """Main function."""
    print("🚨 Quick Fix for 422 Error: /api/audio/tags")
    print("=" * 50)
    print("This script will add the missing tag/category columns")
    print("to fix the 422 Unprocessable Entity error.")
    print()
    
    # Apply the fix
    fix_success = await check_and_fix_tags_columns()
    
    if fix_success:
        # Test the endpoint
        test_success = await test_tags_endpoint()
        
        if test_success:
            print("\n🎉 SUCCESS! The tags endpoint should now work.")
            print("\nNext steps:")
            print("  1. Restart your API server if it's running")
            print("  2. Test the endpoint from your Flutter app")
            print("  3. The 422 error should be resolved")
        else:
            print("\n⚠️  Fix applied but endpoint test failed.")
            print("Check server logs for more details.")
    else:
        print("\n❌ Could not apply the fix.")
        print("Alternative solutions:")
        print("  1. Run the full migration: python3 resolve_migration_error.py")
        print("  2. Use Alembic: alembic stamp 001 && alembic upgrade 002")
        print("  3. Check database connection and permissions")
    
    return fix_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)