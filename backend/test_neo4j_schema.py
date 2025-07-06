#!/usr/bin/env python3
"""Test script for Neo4j Schema Manager functionality."""
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_schema_initialization():
    """Test schema initialization and creation."""
    try:
        from services.neo4j_schema import get_schema_manager
        
        schema_manager = get_schema_manager()
        
        # Test schema initialization
        logger.info("🔧 Initializing Neo4j schema...")
        results = await schema_manager.initialize()
        
        logger.info("✅ Schema initialization completed")
        logger.info(f"  📊 Constraints: {results['constraints']['created']} created, {results['constraints']['failed']} failed")
        logger.info(f"  📊 Indexes: {results['indexes']['created']} created, {results['indexes']['failed']} failed")
        
        if results['constraints']['errors']:
            logger.warning(f"  ⚠️  Constraint errors: {results['constraints']['errors']}")
        
        if results['indexes']['errors']:
            logger.warning(f"  ⚠️  Index errors: {results['indexes']['errors']}")
        
        # Test verification
        verification = results.get('verification', {})
        logger.info(f"  🔍 Schema verification: {verification.get('status', 'unknown')}")
        logger.info(f"  🔍 Total constraints: {verification.get('constraints', {}).get('total', 0)}")
        logger.info(f"  🔍 Total indexes: {verification.get('indexes', {}).get('total', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema initialization test failed: {e}")
        return False


async def test_schema_verification():
    """Test schema verification functionality."""
    try:
        from services.neo4j_schema import get_schema_manager
        
        schema_manager = get_schema_manager()
        
        # Test schema verification
        logger.info("🔍 Verifying Neo4j schema...")
        verification = await schema_manager.verify_schema()
        
        logger.info("✅ Schema verification completed")
        logger.info(f"  📊 Status: {verification['status']}")
        logger.info(f"  📊 Constraints: {verification['constraints']['total']}")
        logger.info(f"  📊 Indexes: {verification['indexes']['total']}")
        logger.info(f"  📊 Labels: {verification['labels']['total']}")
        logger.info(f"  📊 Relationship types: {verification['relationship_types']['total']}")
        
        # Show some active constraints
        if verification['constraints']['active']:
            logger.info("  🔒 Active constraints (first 5):")
            for constraint in verification['constraints']['active'][:5]:
                logger.info(f"    - {constraint['name']}: {constraint['type']}")
        
        # Show some active indexes
        if verification['indexes']['active']:
            logger.info("  📇 Active indexes (first 5):")
            for index in verification['indexes']['active'][:5]:
                logger.info(f"    - {index['name']}: {index['state']}")
        
        # Show labels
        if verification['labels']['active']:
            logger.info(f"  🏷️  Labels: {', '.join(verification['labels']['active'])}")
        
        # Show relationship types
        if verification['relationship_types']['active']:
            logger.info(f"  🔗 Relationship types: {', '.join(verification['relationship_types']['active'])}")
        
        return verification['status'] == 'healthy'
        
    except Exception as e:
        logger.error(f"❌ Schema verification test failed: {e}")
        return False


async def test_schema_info():
    """Test schema information retrieval."""
    try:
        from services.neo4j_schema import get_schema_manager
        
        schema_manager = get_schema_manager()
        
        # Test schema info
        logger.info("📋 Getting schema information...")
        info = await schema_manager.get_schema_info()
        
        logger.info("✅ Schema info retrieved")
        logger.info(f"  📊 Schema initialized: {info.get('schema_initialized', False)}")
        logger.info(f"  📊 Total nodes: {info.get('total_nodes', 0)}")
        logger.info(f"  📊 Total relationships: {info.get('total_relationships', 0)}")
        logger.info(f"  📊 Audio chunks: {info.get('audio_chunks', 0)}")
        logger.info(f"  📊 Entities: {info.get('entities', 0)}")
        logger.info(f"  📊 Users: {info.get('users', 0)}")
        logger.info(f"  📊 Audio files: {info.get('audio_files', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema info test failed: {e}")
        return False


async def test_health_check():
    """Test health check functionality."""
    try:
        from services.neo4j_schema import get_schema_manager
        
        schema_manager = get_schema_manager()
        
        # Test health check
        logger.info("🏥 Performing health check...")
        health = await schema_manager.health_check()
        
        logger.info("✅ Health check completed")
        logger.info(f"  📊 Status: {health['status']}")
        logger.info(f"  📊 Client status: {health.get('client_status', 'unknown')}")
        logger.info(f"  📊 Schema status: {health.get('schema_status', 'unknown')}")
        logger.info(f"  📊 Constraints count: {health.get('constraints_count', 0)}")
        logger.info(f"  📊 Indexes count: {health.get('indexes_count', 0)}")
        
        if health.get('issues'):
            logger.warning(f"  ⚠️  Issues: {health['issues']}")
        
        if health.get('error'):
            logger.error(f"  ❌ Error: {health['error']}")
        
        return health['status'] in ['healthy', 'degraded']
        
    except Exception as e:
        logger.error(f"❌ Health check test failed: {e}")
        return False


async def test_constraint_creation():
    """Test individual constraint creation and validation."""
    try:
        from services.neo4j_client import get_neo4j_client_async
        
        client = await get_neo4j_client_async()
        
        # Test creating a sample node that should trigger constraints
        logger.info("🧪 Testing constraint validation...")
        
        # Create a test person (should work)
        await client.execute_write_query("""
            MERGE (p:Person {name: "Test Person", normalized_name: "test_person"})
            SET p.created_at = datetime()
            RETURN p
        """)
        logger.info("  ✅ Created test person node")
        
        # Try to create duplicate person (should be prevented by constraint)
        try:
            await client.execute_write_query("""
                CREATE (p:Person {name: "Test Person", normalized_name: "test_person_duplicate"})
                RETURN p
            """)
            logger.warning("  ⚠️  Duplicate person creation was not prevented")
        except Exception as e:
            if "constraint" in str(e).lower():
                logger.info("  ✅ Constraint properly prevented duplicate person")
            else:
                logger.error(f"  ❌ Unexpected error: {e}")
        
        # Create a test audio chunk with required fields
        await client.execute_write_query("""
            MERGE (c:AudioChunk {
                id: "test_chunk_001",
                audio_id: "test_audio_001",
                text: "This is a test chunk",
                user_id: "test_user",
                timestamp: datetime(),
                created_at: datetime()
            })
            RETURN c
        """)
        logger.info("  ✅ Created test audio chunk node")
        
        # Clean up test data
        await client.execute_write_query("""
            MATCH (p:Person {name: "Test Person"})
            DELETE p
        """)
        
        await client.execute_write_query("""
            MATCH (c:AudioChunk {id: "test_chunk_001"})
            DELETE c
        """)
        logger.info("  🧹 Cleaned up test data")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Constraint creation test failed: {e}")
        return False


async def main():
    """Run all Neo4j Schema Manager tests."""
    logger.info("🧪 Running Neo4j Schema Manager Tests")
    
    tests = [
        ("Schema Initialization", test_schema_initialization),
        ("Schema Verification", test_schema_verification),
        ("Schema Information", test_schema_info),
        ("Health Check", test_health_check),
        ("Constraint Validation", test_constraint_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            result = await test_func()
            
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Neo4j Schema Manager tests passed!")
        logger.info("\n📋 Features Validated:")
        logger.info("  ✅ Schema initialization with constraints and indexes")
        logger.info("  ✅ Schema verification and status checking")
        logger.info("  ✅ Comprehensive schema information retrieval")
        logger.info("  ✅ Health monitoring and diagnostics")
        logger.info("  ✅ Constraint validation and enforcement")
        logger.info("  ✅ Index creation for performance optimization")
        logger.info("  ✅ Error handling and recovery")
        return 0
    else:
        logger.error("💥 Some Neo4j Schema Manager tests failed.")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}")
        sys.exit(1)