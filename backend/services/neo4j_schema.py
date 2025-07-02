"""Neo4j Schema Manager for Pegasus Brain graph database."""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from services.neo4j_client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


class Neo4jSchemaManager:
    """Manages Neo4j graph schema, constraints, and indexes for Pegasus Brain."""
    
    def __init__(self, client: Neo4jClient = None):
        """Initialize the schema manager.
        
        Args:
            client: Optional Neo4j client instance
        """
        self.client = client
        self._schema_initialized = False
    
    async def initialize(self, force_recreate: bool = False) -> Dict[str, Any]:
        """Initialize the complete Neo4j schema.
        
        Args:
            force_recreate: If True, drop and recreate all schema elements
            
        Returns:
            Dictionary containing initialization results
        """
        if not self.client:
            self.client = await get_neo4j_client()
        
        results = {
            "constraints": {"created": 0, "failed": 0, "errors": []},
            "indexes": {"created": 0, "failed": 0, "errors": []},
            "labels": {"created": 0, "failed": 0, "errors": []},
            "initialization_time": datetime.utcnow().isoformat()
        }
        
        try:
            if force_recreate:
                await self._drop_all_schema()
                logger.info("Dropped existing schema for recreation")
            
            # Create constraints first (they're required for indexes)
            constraint_results = await self._create_all_constraints()
            results["constraints"].update(constraint_results)
            
            # Create indexes for performance
            index_results = await self._create_all_indexes()
            results["indexes"].update(index_results)
            
            # Verify schema is properly set up
            verification = await self.verify_schema()
            results["verification"] = verification
            
            self._schema_initialized = True
            logger.info("Neo4j schema initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            results["error"] = str(e)
            raise
        
        return results
    
    async def _create_all_constraints(self) -> Dict[str, Any]:
        """Create all necessary constraints for the Pegasus Brain schema."""
        constraints = {
            # Entity constraints - ensure uniqueness and data integrity
            "person_name": "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "person_normalized": "CREATE CONSTRAINT person_normalized IF NOT EXISTS FOR (p:Person) REQUIRE p.normalized_name IS UNIQUE",
            
            "location_name": "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "location_normalized": "CREATE CONSTRAINT location_normalized IF NOT EXISTS FOR (l:Location) REQUIRE l.normalized_name IS UNIQUE",
            
            "organization_name": "CREATE CONSTRAINT organization_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            "organization_normalized": "CREATE CONSTRAINT organization_normalized IF NOT EXISTS FOR (o:Organization) REQUIRE o.normalized_name IS UNIQUE",
            
            "topic_name": "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "topic_normalized": "CREATE CONSTRAINT topic_normalized IF NOT EXISTS FOR (t:Topic) REQUIRE t.normalized_name IS UNIQUE",
            
            "project_name": "CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE",
            "project_normalized": "CREATE CONSTRAINT project_normalized IF NOT EXISTS FOR (p:Project) REQUIRE p.normalized_name IS UNIQUE",
            
            "event_name": "CREATE CONSTRAINT event_name IF NOT EXISTS FOR (e:Event) REQUIRE e.name IS UNIQUE",
            "task_name": "CREATE CONSTRAINT task_name IF NOT EXISTS FOR (t:Task) REQUIRE t.name IS UNIQUE",
            
            # Audio chunk constraints - essential for data consistency
            "chunk_id": "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:AudioChunk) REQUIRE c.id IS UNIQUE",
            "chunk_required_fields": "CREATE CONSTRAINT chunk_audio_id IF NOT EXISTS FOR (c:AudioChunk) REQUIRE c.audio_id IS NOT NULL",
            
            # User constraints - data isolation
            "user_id": "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            
            # Audio file constraints
            "audio_file_id": "CREATE CONSTRAINT audio_file_id IF NOT EXISTS FOR (a:AudioFile) REQUIRE a.id IS UNIQUE",
            
            # Relationship constraints for data quality
            "mention_unique": "CREATE CONSTRAINT mention_unique IF NOT EXISTS FOR ()-[r:MENTIONS]-() REQUIRE (r.chunk_id, r.entity_id) IS UNIQUE",
        }
        
        results = {"created": 0, "failed": 0, "errors": []}
        
        for constraint_name, constraint_query in constraints.items():
            try:
                await self.client.execute_write_query(constraint_query)
                results["created"] += 1
                logger.info(f"✅ Created constraint: {constraint_name}")
                
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "equivalent constraint already exists" in error_msg:
                    logger.debug(f"Constraint {constraint_name} already exists")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{constraint_name}: {str(e)}")
                    logger.warning(f"❌ Failed to create constraint {constraint_name}: {e}")
        
        return results
    
    async def _create_all_indexes(self) -> Dict[str, Any]:
        """Create all necessary indexes for performance optimization."""
        indexes = {
            # Text search indexes for semantic queries
            "chunk_text": "CREATE INDEX chunk_text IF NOT EXISTS FOR (c:AudioChunk) ON (c.text)",
            "chunk_summary": "CREATE INDEX chunk_summary IF NOT EXISTS FOR (c:AudioChunk) ON (c.summary)",
            "entity_name": "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "entity_normalized": "CREATE INDEX entity_normalized IF NOT EXISTS FOR (e:Entity) ON (e.normalized_name)",
            
            # Frequency and importance indexes
            "entity_mentions": "CREATE INDEX entity_mentions IF NOT EXISTS FOR (e:Entity) ON (e.mention_count)",
            "entity_confidence": "CREATE INDEX entity_confidence IF NOT EXISTS FOR (e:Entity) ON (e.confidence_score)",
            "chunk_importance": "CREATE INDEX chunk_importance IF NOT EXISTS FOR (c:AudioChunk) ON (c.importance_score)",
            
            # Temporal indexes for time-based queries
            "chunk_timestamp": "CREATE INDEX chunk_timestamp IF NOT EXISTS FOR (c:AudioChunk) ON (c.timestamp)",
            "chunk_date": "CREATE INDEX chunk_date IF NOT EXISTS FOR (c:AudioChunk) ON (c.date)",
            "chunk_created": "CREATE INDEX chunk_created IF NOT EXISTS FOR (c:AudioChunk) ON (c.created_at)",
            "entity_first_seen": "CREATE INDEX entity_first_seen IF NOT EXISTS FOR (e:Entity) ON (e.first_seen_at)",
            "entity_last_seen": "CREATE INDEX entity_last_seen IF NOT EXISTS FOR (e:Entity) ON (e.last_seen_at)",
            
            # User data isolation indexes
            "chunk_user": "CREATE INDEX chunk_user IF NOT EXISTS FOR (c:AudioChunk) ON (c.user_id)",
            "entity_user": "CREATE INDEX entity_user IF NOT EXISTS FOR (e:Entity) ON (e.user_id)",
            "audio_user": "CREATE INDEX audio_user IF NOT EXISTS FOR (a:AudioFile) ON (a.user_id)",
            
            # Content categorization indexes
            "chunk_language": "CREATE INDEX chunk_language IF NOT EXISTS FOR (c:AudioChunk) ON (c.language)",
            "chunk_sentiment": "CREATE INDEX chunk_sentiment IF NOT EXISTS FOR (c:AudioChunk) ON (c.sentiment_score)",
            "entity_type": "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "entity_category": "CREATE INDEX entity_category IF NOT EXISTS FOR (e:Entity) ON (e.category)",
            
            # Audio file metadata indexes
            "audio_filename": "CREATE INDEX audio_filename IF NOT EXISTS FOR (a:AudioFile) ON (a.filename)",
            "audio_duration": "CREATE INDEX audio_duration IF NOT EXISTS FOR (a:AudioFile) ON (a.duration)",
            "audio_created": "CREATE INDEX audio_created IF NOT EXISTS FOR (a:AudioFile) ON (a.created_at)",
            
            # Relationship indexes for graph traversal performance
            "mention_confidence": "CREATE INDEX mention_confidence IF NOT EXISTS FOR ()-[r:MENTIONS]-() ON (r.confidence)",
            "mention_position": "CREATE INDEX mention_position IF NOT EXISTS FOR ()-[r:MENTIONS]-() ON (r.start_position)",
            "relationship_strength": "CREATE INDEX relationship_strength IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.strength)",
        }
        
        results = {"created": 0, "failed": 0, "errors": []}
        
        for index_name, index_query in indexes.items():
            try:
                await self.client.execute_write_query(index_query)
                results["created"] += 1
                logger.info(f"✅ Created index: {index_name}")
                
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "equivalent index already exists" in error_msg:
                    logger.debug(f"Index {index_name} already exists")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{index_name}: {str(e)}")
                    logger.warning(f"❌ Failed to create index {index_name}: {e}")
        
        return results
    
    async def verify_schema(self) -> Dict[str, Any]:
        """Verify that the schema is properly set up."""
        verification = {
            "constraints": {"total": 0, "active": []},
            "indexes": {"total": 0, "active": []},
            "labels": {"total": 0, "active": []},
            "relationship_types": {"total": 0, "active": []},
            "status": "unknown"
        }
        
        try:
            # Check constraints
            constraints_result = await self.client.execute_query("SHOW CONSTRAINTS")
            verification["constraints"]["total"] = len(constraints_result)
            verification["constraints"]["active"] = [
                {
                    "name": c.get("name", "unknown"),
                    "type": c.get("type", "unknown"),
                    "entity_type": c.get("entityType", "unknown")
                }
                for c in constraints_result
            ]
            
            # Check indexes
            indexes_result = await self.client.execute_query("SHOW INDEXES")
            verification["indexes"]["total"] = len(indexes_result)
            verification["indexes"]["active"] = [
                {
                    "name": i.get("name", "unknown"),
                    "state": i.get("state", "unknown"),
                    "type": i.get("type", "unknown")
                }
                for i in indexes_result
            ]
            
            # Check labels
            labels_result = await self.client.execute_query("CALL db.labels()")
            labels = [r["label"] for r in labels_result]
            verification["labels"]["total"] = len(labels)
            verification["labels"]["active"] = labels
            
            # Check relationship types
            rel_types_result = await self.client.execute_query("CALL db.relationshipTypes()")
            rel_types = [r["relationshipType"] for r in rel_types_result]
            verification["relationship_types"]["total"] = len(rel_types)
            verification["relationship_types"]["active"] = rel_types
            
            # Determine overall status
            expected_min_constraints = 10  # Minimum expected constraints
            expected_min_indexes = 15     # Minimum expected indexes
            
            if (verification["constraints"]["total"] >= expected_min_constraints and
                verification["indexes"]["total"] >= expected_min_indexes):
                verification["status"] = "healthy"
            else:
                verification["status"] = "incomplete"
            
            logger.info(f"Schema verification completed: {verification['status']}")
            
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            verification["status"] = "error"
            verification["error"] = str(e)
        
        return verification
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current schema."""
        info = {
            "schema_initialized": self._schema_initialized,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Get database statistics
            stats_queries = {
                "total_nodes": "MATCH (n) RETURN count(n) as count",
                "total_relationships": "MATCH ()-[r]->() RETURN count(r) as count",
                "audio_chunks": "MATCH (c:AudioChunk) RETURN count(c) as count",
                "entities": "MATCH (e:Entity) RETURN count(e) as count",
                "users": "MATCH (u:User) RETURN count(u) as count",
                "audio_files": "MATCH (a:AudioFile) RETURN count(a) as count"
            }
            
            for stat_name, query in stats_queries.items():
                try:
                    result = await self.client.execute_query(query)
                    info[stat_name] = result[0]["count"] if result else 0
                except Exception as e:
                    logger.warning(f"Failed to get {stat_name}: {e}")
                    info[stat_name] = 0
            
            # Add verification results
            info.update(await self.verify_schema())
            
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            info["error"] = str(e)
        
        return info
    
    async def _drop_all_schema(self) -> None:
        """Drop all schema elements. Use with caution!"""
        try:
            # Drop all constraints
            constraints = await self.client.execute_query("SHOW CONSTRAINTS")
            for constraint in constraints:
                try:
                    constraint_name = constraint.get("name", "")
                    if constraint_name:
                        await self.client.execute_write_query(f"DROP CONSTRAINT {constraint_name}")
                        logger.info(f"Dropped constraint: {constraint_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop constraint: {e}")
            
            # Drop all indexes
            indexes = await self.client.execute_query("SHOW INDEXES")
            for index in indexes:
                try:
                    index_name = index.get("name", "")
                    if index_name and not index_name.startswith("__"):  # Skip system indexes
                        await self.client.execute_write_query(f"DROP INDEX {index_name}")
                        logger.info(f"Dropped index: {index_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop index: {e}")
            
        except Exception as e:
            logger.error(f"Failed to drop schema: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the schema."""
        health = {
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check if client is connected
            if not self.client:
                self.client = await get_neo4j_client()
            
            client_health = await self.client.health_check()
            health["client_status"] = client_health["status"]
            
            if client_health["status"] == "healthy":
                # Check schema completeness
                verification = await self.verify_schema()
                health["schema_status"] = verification["status"]
                health["constraints_count"] = verification["constraints"]["total"]
                health["indexes_count"] = verification["indexes"]["total"]
                
                if verification["status"] == "healthy":
                    health["status"] = "healthy"
                else:
                    health["status"] = "degraded"
                    health["issues"] = "Schema incomplete"
            else:
                health["status"] = "unhealthy"
                health["issues"] = "Client connection failed"
            
        except Exception as e:
            logger.error(f"Schema health check failed: {e}")
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health


def get_schema_manager() -> Neo4jSchemaManager:
    """Get a Neo4j Schema Manager instance.
    
    Returns:
        Neo4j Schema Manager instance
    """
    return Neo4jSchemaManager()