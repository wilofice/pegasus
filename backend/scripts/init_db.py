#!/usr/bin/env python3
"""Initialize the database with tables."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import engine
from models.base import Base
# Import all models to register them with Base.metadata
from models import AudioFile, ProcessingJob, JobStatusHistory, ConversationHistory


async def init_db():
    """Create all database tables."""
    async with engine.begin() as conn:
        # Drop all tables (for development only!)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())