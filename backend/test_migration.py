#!/usr/bin/env python3
"""Test script for database migration."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from models.job import ProcessingJob, JobStatusHistory, JobStatus, JobType
from repositories.job_repository import JobRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_job_models():
    """Test job model creation and operations."""
    logger.info("Testing job models...")
    
    try:
        # Create a job repository (this will test the models)
        job_repo = JobRepository()
        
        # Test creating a job
        job = job_repo.create_job(
            job_type=JobType.TRANSCRIPT_PROCESSING,
            input_data={"test": "data"},
            user_id="test_user",
            priority=1
        )
        
        logger.info(f"✓ Created job: {job.id}")
        
        # Test updating job status
        success = job_repo.update_job_status(
            job.id,
            JobStatus.PROCESSING,
            message="Test status update"
        )
        
        if success:
            logger.info("✓ Updated job status")
        else:
            logger.error("✗ Failed to update job status")
            return False
        
        # Test getting job
        retrieved_job = job_repo.get_job(job.id, include_history=True)
        if retrieved_job:
            logger.info(f"✓ Retrieved job: {retrieved_job.status}")
            logger.info(f"✓ Job has {len(retrieved_job.status_history)} history entries")
        else:
            logger.error("✗ Failed to retrieve job")
            return False
        
        # Test job statistics
        stats = job_repo.get_job_statistics()
        logger.info(f"✓ Job statistics: {stats}")
        
        # Test queue status
        queue_status = job_repo.get_queue_status()
        logger.info(f"✓ Queue status: {queue_status}")
        
        logger.info("✓ All job model tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Job model test failed: {e}")
        return False


def main():
    """Run migration tests."""
    logger.info("🧪 Testing database migration...")
    
    # Test job models
    if not test_job_models():
        logger.error("❌ Job model tests failed!")
        return 1
    
    logger.info("🎉 All migration tests passed!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)