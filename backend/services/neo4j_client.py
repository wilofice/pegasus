"""Neo4j database client for graph operations."""
import logging
from typing import Any, Dict, List, Optional
import asyncio
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client with connection pooling and error handling."""
    
    def __init__(
        self, 
        uri: str = None, 
        user: str = None, 
        password: str = None,
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: int = 60
    ):
        self.uri = uri or getattr(settings, 'neo4j_uri', 'bolt://localhost:7687')
        self.user = user or getattr(settings, 'neo4j_user', 'neo4j')
        self.password = password or getattr(settings, 'neo4j_password', 'pegasus_neo4j_password')
        
        self._driver: Optional[AsyncDriver] = None
        self._connection_config = {
            'max_connection_lifetime': max_connection_lifetime,
            'max_connection_pool_size': max_connection_pool_size,
            'connection_acquisition_timeout': connection_acquisition_timeout
        }
    
    async def connect(self) -> None:
        """Initialize the Neo4j driver with connection pooling."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                **self._connection_config
            )
            
            # Test the connection
            await self.health_check()
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
            
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self) -> None:
        """Close the Neo4j driver and all connections."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    @asynccontextmanager
    async def session(self, database: str = None, **kwargs):
        """Context manager for Neo4j sessions."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        
        session = self._driver.session(database=database, **kwargs)
        try:
            yield session
        finally:
            await session.close()
    
    async def execute_query(
        self, 
        query: str, 
        parameters: Dict[str, Any] = None,
        database: str = None
    ) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        
        parameters = parameters or {}
        
        try:
            async with self.session(database=database) as session:
                result = await session.run(query, parameters)
                records = await result.data()
                return records
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    async def execute_write_query(
        self, 
        query: str, 
        parameters: Dict[str, Any] = None,
        database: str = None
    ) -> List[Dict[str, Any]]:
        """Execute a write query in a transaction."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        
        parameters = parameters or {}
        
        try:
            async with self.session(database=database) as session:
                result = await session.execute_write(
                    self._write_transaction, query, parameters
                )
                return result
                
        except Exception as e:
            logger.error(f"Write query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    @staticmethod
    async def _write_transaction(tx, query: str, parameters: Dict[str, Any]):
        """Execute a write transaction."""
        result = await tx.run(query, parameters)
        return await result.data()
    
    async def execute_read_query(
        self, 
        query: str, 
        parameters: Dict[str, Any] = None,
        database: str = None
    ) -> List[Dict[str, Any]]:
        """Execute a read query in a transaction."""
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        
        parameters = parameters or {}
        
        try:
            async with self.session(database=database) as session:
                result = await session.execute_read(
                    self._read_transaction, query, parameters
                )
                return result
                
        except Exception as e:
            logger.error(f"Read query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    @staticmethod
    async def _read_transaction(tx, query: str, parameters: Dict[str, Any]):
        """Execute a read transaction."""
        result = await tx.run(query, parameters)
        return await result.data()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the Neo4j connection."""
        try:
            result = await self.execute_query("RETURN 1 AS health_check")
            if result and result[0].get('health_check') == 1:
                return {
                    "status": "healthy",
                    "uri": self.uri,
                    "user": self.user
                }
            else:
                return {"status": "unhealthy", "error": "Unexpected response"}
                
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get Neo4j database information."""
        try:
            queries = {
                "version": "CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version",
                "node_count": "MATCH (n) RETURN count(n) as node_count",
                "relationship_count": "MATCH ()-[r]->() RETURN count(r) as relationship_count",
                "labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
                "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
            }
            
            info = {}
            for key, query in queries.items():
                try:
                    result = await self.execute_query(query)
                    if result:
                        if key == "version":
                            info[key] = f"{result[0]['name']} {result[0]['version']}"
                        elif key in ["labels", "relationship_types"]:
                            info[key] = result[0].get(key, []) if result[0] else []
                        else:
                            info[key] = result[0].get(key, 0) if result[0] else 0
                except Exception as e:
                    logger.warning(f"Failed to get {key}: {e}")
                    info[key] = "unknown"
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}
    
    async def create_constraints(self) -> None:
        """Create necessary constraints for the Pegasus Brain schema."""
        constraints = [
            # Entity constraints
            "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT organization_name IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE",
            
            # General Entity constraint for all entity types
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT entity_normalized_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.normalized_name IS UNIQUE",
            
            # Chunk constraints
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:AudioChunk) REQUIRE c.id IS UNIQUE",
            # Note: Property existence constraints require Neo4j Enterprise Edition
            # "CREATE CONSTRAINT chunk_audio_id IF NOT EXISTS FOR (c:AudioChunk) REQUIRE c.audio_id IS NOT NULL",
            
            # User constraints
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
        ]
        
        for constraint in constraints:
            try:
                await self.execute_write_query(constraint)
                logger.info(f"Created constraint: {constraint.split('FOR')[0].strip()}")
            except Exception as e:
                # Constraint might already exist
                if "already exists" not in str(e).lower():
                    logger.warning(f"Failed to create constraint: {e}")
    
    async def create_indexes(self) -> None:
        """Create necessary indexes for performance."""
        indexes = [
            # Text search indexes
            "CREATE INDEX audio_chunk_text IF NOT EXISTS FOR (c:AudioChunk) ON (c.text)",
            "CREATE INDEX entity_mentions IF NOT EXISTS FOR (e:Entity) ON (e.mention_count)",
            
            # Temporal indexes
            "CREATE INDEX chunk_timestamp IF NOT EXISTS FOR (c:AudioChunk) ON (c.timestamp)",
            "CREATE INDEX chunk_date IF NOT EXISTS FOR (c:AudioChunk) ON (c.date)",
            
            # User data indexes
            "CREATE INDEX chunk_user_id IF NOT EXISTS FOR (c:AudioChunk) ON (c.user_id)",
            "CREATE INDEX entity_user_id IF NOT EXISTS FOR (e:Entity) ON (e.user_id)"
        ]
        
        for index in indexes:
            try:
                await self.execute_write_query(index)
                logger.info(f"Created index: {index.split('FOR')[0].strip()}")
            except Exception as e:
                # Index might already exist
                if "already exists" not in str(e).lower():
                    logger.warning(f"Failed to create index: {e}")


# Global Neo4j client instance
_neo4j_client: Optional[Neo4jClient] = None

def get_neo4j_client() -> Neo4jClient:
    """Get or create the global Neo4j client instance (synchronous version for Celery tasks)."""
    global _neo4j_client
    
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        
        # Use asyncio to run async initialization in sync context
        import asyncio
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g., in async context), create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _initialize_neo4j_client(_neo4j_client))
                    future.result()
            else:
                # Run in the current loop
                loop.run_until_complete(_initialize_neo4j_client(_neo4j_client))
        except RuntimeError:
            # No event loop exists, create one
            asyncio.run(_initialize_neo4j_client(_neo4j_client))
    
    return _neo4j_client

async def get_neo4j_client_async() -> Neo4jClient:
    """Get or create the global Neo4j client instance (async version)."""
    global _neo4j_client
    
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _initialize_neo4j_client(_neo4j_client)
    
    return _neo4j_client

async def _initialize_neo4j_client(client: Neo4jClient) -> None:
    """Initialize Neo4j client with connection and schema setup."""
    await client.connect()
    
    # Initialize schema
    await client.create_constraints()
    await client.create_indexes()

async def close_neo4j_client() -> None:
    """Close the global Neo4j client."""
    global _neo4j_client
    
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None