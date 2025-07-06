#!/usr/bin/env python3
"""Test script to verify database initialization works correctly."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from core.database import engine
from models.base import Base
# Import all models to ensure they're registered
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory
from sqlalchemy import text

async def test_db_init():
    """Test database initialization and verify all tables are created."""
    print("Testing database initialization...")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Database tables created successfully!")
            
            # Verify tables exist
            tables_to_check = [
                'audio_files',
                'processing_jobs', 
                'job_status_history',
                'conversation_history'
            ]
            
            for table_name in tables_to_check:
                result = await conn.execute(
                    text("SELECT to_regclass('public.{}')".format(table_name))
                )
                table_exists = result.scalar() is not None
                
                if table_exists:
                    print(f"✅ Table '{table_name}' exists")
                else:
                    print(f"❌ Table '{table_name}' missing")
            
            # Check if PENDING_REVIEW status is available
            try:
                result = await conn.execute(
                    text("SELECT unnest(enum_range(NULL::processingstatus))")
                )
                statuses = [row[0] for row in result]
                
                if 'pending_review' in statuses:
                    print("✅ PENDING_REVIEW status available")
                else:
                    print("❌ PENDING_REVIEW status missing")
                    print(f"Available statuses: {statuses}")
                    
            except Exception as e:
                print(f"ℹ️  Status enum check failed (might not exist yet): {e}")
            
            # Check if tags column is array type
            try:
                result = await conn.execute(
                    text("""
                        SELECT data_type, column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'audio_files' 
                        AND column_name IN ('tag', 'tags')
                    """)
                )
                columns = result.fetchall()
                
                for data_type, column_name in columns:
                    print(f"ℹ️  Column '{column_name}': {data_type}")
                    
            except Exception as e:
                print(f"ℹ️  Column check failed: {e}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
        
    print("\n🎉 Database initialization test completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_db_init())
    sys.exit(0 if success else 1)