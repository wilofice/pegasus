#!/usr/bin/env python3
"""Initialize the database with tables.

Usage:
    python init_db.py              # Create tables only
    python init_db.py --with-alembic # Create tables and mark migrations as applied
    python init_db.py --drop       # Drop and recreate all tables (DANGEROUS!)
"""
import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import engine
from models.base import Base
# Import all models to register them with Base.metadata
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory, JobStatus, session_transcript, user_session
from sqlalchemy import text


async def init_db(drop_first=False, mark_migrations=False):
    """Create all database tables."""
    async with engine.begin() as conn:
        if drop_first:
            print("⚠️  Dropping all existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ All tables dropped")
        
        # Create all tables
        print("🔨 Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        
        # Verify tables were created
        tables_created = []
        expected_tables = ['audio_files', 'processing_jobs', 'job_status_history', 'conversation_history', 'session_transcripts', 'user_sessions']
        
        for table_name in expected_tables:
            try:
                # Try using to_regclass (PostgreSQL 9.4+)
                result = await conn.execute(
                    text("SELECT to_regclass('public.{}')".format(table_name))
                )
                if result.scalar() is not None:
                    tables_created.append(table_name)
            except Exception:
                # Fallback for older PostgreSQL versions
                result = await conn.execute(
                    text("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = '{}'
                    """.format(table_name))
                )
                if result.scalar() is not None:
                    tables_created.append(table_name)
        
        print(f"✅ Created {len(tables_created)} tables: {', '.join(tables_created)}")
        
        if mark_migrations:
            print("📝 Marking migrations as applied...")
            try:
                # Create alembic_version table if it doesn't exist
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))
                
                # Mark the latest migration as applied
                await conn.execute(text("""
                    INSERT INTO alembic_version (version_num) 
                    VALUES ('006_conversation_history_tags')
                    ON CONFLICT (version_num) DO NOTHING
                """))
                
                print("✅ Marked migration 006_conversation_history_tags as applied")
            except Exception as e:
                print(f"⚠️  Could not mark migrations: {e}")
        
        print("\n🎉 Database initialization completed!")
        
        if not mark_migrations:
            print("\n💡 Note: If you want to use Alembic migrations later, run:")
            print("   alembic stamp head")


def main():
    parser = argparse.ArgumentParser(description="Initialize Pegasus database")
    parser.add_argument('--drop', action='store_true', 
                       help='Drop all tables before creating (DANGEROUS!)')
    parser.add_argument('--with-alembic', action='store_true',
                       help='Mark current migration as applied after creating tables')
    
    args = parser.parse_args()
    
    if args.drop:
        confirm = input("⚠️  This will DELETE ALL DATA! Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return
    
    asyncio.run(init_db(drop_first=args.drop, mark_migrations=args.with_alembic))


if __name__ == "__main__":
    main()