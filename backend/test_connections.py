#!/usr/bin/env python3
"""Test script for database connections."""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.neo4j_client import get_neo4j_client_async, close_neo4j_client
from services.vector_db_client import get_chromadb_client, close_chromadb_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_neo4j():
    """Test Neo4j connection."""
    logger.info("Testing Neo4j connection...")
    
    try:
        client = await get_neo4j_client_async()
        health = await client.health_check()
        
        if health["status"] == "healthy":
            logger.info("✓ Neo4j connection successful")
            
            # Test basic query
            result = await client.execute_query("RETURN 'Hello Neo4j' AS message")
            logger.info(f"✓ Query result: {result[0]['message']}")
            
            # Get database info
            info = await client.get_database_info()
            logger.info(f"✓ Database info: {info}")
            
        else:
            logger.error(f"✗ Neo4j health check failed: {health}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Neo4j connection failed: {e}")
        return False
    
    return True


async def test_chromadb():
    """Test ChromaDB connection."""
    logger.info("Testing ChromaDB connection...")
    
    try:
        client = get_chromadb_client()
        health = await client.health_check()
        
        if health["status"] == "healthy":
            logger.info("✓ ChromaDB connection successful")
            
            # Test collection info
            info = await client.get_collection_info()
            logger.info(f"✓ Collection info: {info}")
            
            # Test embedding
            embedding = client.embed_text("Hello ChromaDB")
            logger.info(f"✓ Embedding generated: {len(embedding)} dimensions")
            
        else:
            logger.error(f"✗ ChromaDB health check failed: {health}")
            return False
            
    except Exception as e:
        logger.error(f"✗ ChromaDB connection failed: {e}")
        return False
    
    return True


async def main():
    """Run all connection tests."""
    logger.info("🧪 Testing Pegasus Brain database connections...")
    
    results = []
    
    # Test Neo4j
    neo4j_ok = await test_neo4j()
    results.append(("Neo4j", neo4j_ok))
    
    # Test ChromaDB
    chromadb_ok = await test_chromadb()
    results.append(("ChromaDB", chromadb_ok))
    
    # Cleanup
    await close_neo4j_client()
    close_chromadb_client()
    
    # Summary
    logger.info("\n📊 Test Results:")
    all_passed = True
    
    for service, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {service}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All database connections successful!")
        return 0
    else:
        logger.error("\n❌ Some database connections failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)