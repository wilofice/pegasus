"""Neo4j Graph Retriever implementation for relationship-based search in knowledge graphs."""
import logging
from typing import List, Dict, Any, Optional, Set, Union
from datetime import datetime
import uuid

from services.retrieval.base import BaseRetriever, RetrievalResult, RetrievalFilter, ResultType, FilterOperator
from services.neo4j_client import get_neo4j_client_async

logger = logging.getLogger(__name__)


class Neo4jRetriever(BaseRetriever):
    """Graph traversal and relationship-based search implementation for Neo4j."""
    
    def __init__(self, 
                 default_depth: int = 2,
                 max_depth: int = 5,
                 result_limit: int = 100,
                 **kwargs):
        """Initialize Neo4j retriever.
        
        Args:
            default_depth: Default relationship traversal depth
            max_depth: Maximum allowed traversal depth
            result_limit: Maximum results per query
            **kwargs: Additional arguments passed to base class
        """
        super().__init__("Neo4jRetriever")
        self.default_depth = default_depth
        self.max_depth = max_depth
        self.result_limit = result_limit
        self.neo4j_client = None
    
    async def initialize(self) -> None:
        """Initialize Neo4j connection."""
        try:
            # Get Neo4j client instance
            self.neo4j_client = await get_neo4j_client_async()
            logger.info("Neo4j retriever initialized successfully")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j retriever: {e}")
            raise
    
    async def search(self, 
                    query: str, 
                    filters: List[RetrievalFilter] = None,
                    limit: int = 10,
                    **kwargs) -> List[RetrievalResult]:
        """Search for content using graph traversal and entity relationships.
        
        Args:
            query: Search query (entity name, topic, or general text)
            filters: List of filters to apply
            limit: Maximum number of results to return
            **kwargs: Additional search parameters (depth, relationship_types, entity_types, user_id)
            
        Returns:
            List of RetrievalResult objects from graph traversal
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Extract search parameters
            depth = min(kwargs.get('depth', self.default_depth), self.max_depth)
            relationship_types = kwargs.get('relationship_types', [])
            entity_types = kwargs.get('entity_types', [])
            user_id = kwargs.get('user_id')
            
            # Try different search strategies based on query type
            results = []
            
            # Strategy 1: Direct entity name search
            entity_results = await self._search_by_entity_name(
                query, depth, relationship_types, user_id, limit
            )
            results.extend(entity_results)
            
            # Strategy 2: Text-based entity search (fuzzy matching)
            if len(results) < limit:
                fuzzy_results = await self._search_by_text_content(
                    query, depth, user_id, limit - len(results)
                )
                results.extend(fuzzy_results)
            
            # Strategy 3: Relationship path search
            if len(results) < limit:
                path_results = await self._search_relationship_paths(
                    query, depth, relationship_types, user_id, limit - len(results)
                )
                results.extend(path_results)
            
            # Apply additional filters
            if filters:
                results = self._apply_additional_filters(results, filters)
            
            # Remove duplicates and rank by relevance
            results = self.deduplicate_results(results)
            results = self._rank_graph_results(results, query)
            
            # Limit final results
            results = results[:limit]
            
            logger.info(f"Neo4j search returned {len(results)} results for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return []
    
    async def get_by_id(self, id: str) -> Optional[RetrievalResult]:
        """Retrieve a specific node by its ID.
        
        Args:
            id: Node ID (can be chunk ID, entity ID, or internal Neo4j ID)
            
        Returns:
            RetrievalResult if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Try to find by chunk ID first
            chunk_query = """
            MATCH (c:AudioChunk {id: $id})
            OPTIONAL MATCH (c)-[:MENTIONS]->(e)
            RETURN c, collect(DISTINCT {
                id: id(e),
                type: labels(e)[0],
                name: e.name,
                normalized_name: e.normalized_name
            }) as entities
            """
            
            result = await self.neo4j_client.execute_read_query(chunk_query, {"id": id})
            
            if result and result[0]['c']:
                chunk_data = dict(result[0]['c'])
                entities = result[0]['entities']
                
                return RetrievalResult(
                    id=chunk_data.get('id', id),
                    type=ResultType.CHUNK,
                    content=chunk_data.get('text', ''),
                    metadata=self._clean_node_properties(chunk_data),
                    score=1.0,  # Perfect match by ID
                    source=f"neo4j.chunk",
                    timestamp=self._parse_timestamp(chunk_data.get('created_at')),
                    entities=entities if entities[0].get('id') else []
                )
            
            # Try to find by entity name/normalized name
            entity_query = """
            MATCH (e) 
            WHERE e.name = $id OR e.normalized_name = $id OR id(e) = toInteger($id)
            RETURN e, labels(e) as types
            """
            
            result = await self.neo4j_client.execute_read_query(entity_query, {"id": id})
            
            if result and result[0]['e']:
                entity_data = dict(result[0]['e'])
                entity_types = result[0]['types']
                
                return RetrievalResult(
                    id=str(entity_data.get('normalized_name', id)),
                    type=ResultType.ENTITY,
                    content=entity_data.get('name', ''),
                    metadata={
                        **self._clean_node_properties(entity_data),
                        'entity_types': entity_types
                    },
                    score=1.0,
                    source=f"neo4j.entity",
                    timestamp=self._parse_timestamp(entity_data.get('created_at'))
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get node by ID {id}: {e}")
            return None
    
    async def find_entity_mentions(self, 
                                  entity_name: str, 
                                  entity_type: str = None,
                                  user_id: str = None,
                                  limit: int = 20) -> List[RetrievalResult]:
        """Find all chunks that mention a specific entity.
        
        Args:
            entity_name: Name of the entity to search for
            entity_type: Optional entity type filter (Person, Organization, etc.)
            user_id: Optional user ID for data isolation
            limit: Maximum number of results
            
        Returns:
            List of chunks mentioning the entity
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build query with optional type and user filters
            type_filter = f":{entity_type}" if entity_type else ""
            user_filter = "AND c.user_id = $user_id" if user_id else ""
            
            query = f"""
            MATCH (e{type_filter})
            WHERE e.name =~ $entity_pattern OR e.normalized_name =~ $normalized_pattern
            MATCH (c:AudioChunk)-[:MENTIONS]->(e)
            {user_filter.replace('AND', 'WHERE') if not user_id else user_filter}
            RETURN DISTINCT c, e, 
                   count{{(c)-[:MENTIONS]->()}} as entity_count,
                   e.mention_count as entity_frequency
            ORDER BY entity_frequency DESC, entity_count DESC
            LIMIT $limit
            """
            
            # Create case-insensitive patterns
            normalized_name = entity_name.lower().strip()
            params = {
                "entity_pattern": f"(?i).*{entity_name}.*",
                "normalized_pattern": f".*{normalized_name}.*",
                "limit": limit
            }
            
            if user_id:
                params["user_id"] = user_id
            
            results = await self.neo4j_client.execute_read_query(query, params)
            
            retrieval_results = []
            for result in results:
                chunk_data = dict(result['c'])
                entity_data = dict(result['e'])
                entity_count = result['entity_count']
                entity_frequency = result['entity_frequency']
                
                # Calculate relevance score based on entity frequency and chunk entity count
                score = min(1.0, (entity_frequency / 10.0) + (entity_count / 20.0))
                
                retrieval_result = RetrievalResult(
                    id=chunk_data.get('id', str(uuid.uuid4())),
                    type=ResultType.CHUNK,
                    content=chunk_data.get('text', ''),
                    metadata={
                        **self._clean_node_properties(chunk_data),
                        'matched_entity': entity_data.get('name'),
                        'entity_type': entity_data.get('type'),
                        'entity_frequency': entity_frequency,
                        'chunk_entity_count': entity_count
                    },
                    score=score,
                    source="neo4j.entity_mentions",
                    timestamp=self._parse_timestamp(chunk_data.get('created_at')),
                    entities=[{
                        'name': entity_data.get('name'),
                        'type': entity_data.get('type'),
                        'frequency': entity_frequency
                    }]
                )
                
                retrieval_results.append(retrieval_result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Failed to find entity mentions for {entity_name}: {e}")
            return []
    
    async def find_connections(self, 
                              entity_name: str, 
                              depth: int = None,
                              relationship_types: List[str] = None,
                              user_id: str = None,
                              limit: int = 50) -> List[RetrievalResult]:
        """Find entities and chunks connected to a given entity within specified depth.
        
        Args:
            entity_name: Starting entity name
            depth: Maximum relationship depth (default: self.default_depth)
            relationship_types: Optional list of relationship types to traverse
            user_id: Optional user ID for data isolation
            limit: Maximum number of results
            
        Returns:
            List of connected entities and chunks
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            depth = min(depth or self.default_depth, self.max_depth)
            
            # Build relationship type filter
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            # Build user filter
            user_filter = "WHERE connected.user_id = $user_id OR NOT EXISTS(connected.user_id)" if user_id else ""
            
            query = f"""
            MATCH (start)
            WHERE start.name =~ $entity_pattern OR start.normalized_name =~ $normalized_pattern
            MATCH path = (start)-[r{rel_filter}*1..{depth}]-(connected)
            {user_filter}
            WITH connected, start, path, length(path) as distance
            RETURN DISTINCT connected, 
                   labels(connected) as types,
                   distance,
                   type(relationships(path)[0]) as first_relationship,
                   count{{(connected)-[]->()}} + count{{(connected)<-[]->()}} as connection_count
            ORDER BY distance ASC, connection_count DESC
            LIMIT $limit
            """
            
            normalized_name = entity_name.lower().strip()
            params = {
                "entity_pattern": f"(?i).*{entity_name}.*",
                "normalized_pattern": f".*{normalized_name}.*",
                "limit": limit
            }
            
            if user_id:
                params["user_id"] = user_id
            
            results = await self.neo4j_client.execute_read_query(query, params)
            
            retrieval_results = []
            for result in results:
                connected_data = dict(result['connected'])
                types = result['types']
                distance = result['distance']
                first_relationship = result['first_relationship']
                connection_count = result['connection_count']
                
                # Determine result type
                result_type = ResultType.CHUNK if 'AudioChunk' in types else ResultType.ENTITY
                
                # Calculate relevance score (closer distance and more connections = higher score)
                score = max(0.1, 1.0 / distance) * min(1.0, connection_count / 10.0)
                
                # Extract content based on type
                content = connected_data.get('text') if result_type == ResultType.CHUNK else connected_data.get('name', '')
                
                retrieval_result = RetrievalResult(
                    id=connected_data.get('id', connected_data.get('normalized_name', str(uuid.uuid4()))),
                    type=result_type,
                    content=content,
                    metadata={
                        **self._clean_node_properties(connected_data),
                        'connection_distance': distance,
                        'first_relationship': first_relationship,
                        'total_connections': connection_count,
                        'node_types': types,
                        'connected_from': entity_name
                    },
                    score=score,
                    source=f"neo4j.connections.depth_{distance}",
                    timestamp=self._parse_timestamp(connected_data.get('created_at')),
                    relationships=[{
                        'type': first_relationship,
                        'distance': distance,
                        'source': entity_name
                    }]
                )
                
                retrieval_results.append(retrieval_result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Failed to find connections for {entity_name}: {e}")
            return []
    
    async def _search_by_entity_name(self, 
                                    query: str, 
                                    depth: int,
                                    relationship_types: List[str],
                                    user_id: str,
                                    limit: int) -> List[RetrievalResult]:
        """Search for entities by name and find their mentions."""
        try:
            # Find entity mentions
            mentions = await self.find_entity_mentions(
                entity_name=query,
                user_id=user_id,
                limit=min(limit, 20)
            )
            
            # Find connections if we have room for more results
            if len(mentions) < limit:
                connections = await self.find_connections(
                    entity_name=query,
                    depth=depth,
                    relationship_types=relationship_types,
                    user_id=user_id,
                    limit=limit - len(mentions)
                )
                mentions.extend(connections)
            
            return mentions
            
        except Exception as e:
            logger.error(f"Entity name search failed: {e}")
            return []
    
    async def _search_by_text_content(self, 
                                     query: str, 
                                     depth: int,
                                     user_id: str,
                                     limit: int) -> List[RetrievalResult]:
        """Search for chunks by text content and explore their entity relationships."""
        try:
            user_filter = "AND c.user_id = $user_id" if user_id else ""
            
            text_query = f"""
            MATCH (c:AudioChunk)
            WHERE c.text =~ $text_pattern
            {user_filter.replace('AND', 'WHERE') if not user_id else user_filter}
            OPTIONAL MATCH (c)-[:MENTIONS]->(e)
            RETURN c, collect(DISTINCT {{
                name: e.name,
                type: labels(e)[0],
                normalized_name: e.normalized_name
            }}) as entities
            ORDER BY c.created_at DESC
            LIMIT $limit
            """
            
            params = {
                "text_pattern": f"(?i).*{query}.*",
                "limit": limit
            }
            
            if user_id:
                params["user_id"] = user_id
            
            results = await self.neo4j_client.execute_read_query(text_query, params)
            
            retrieval_results = []
            for result in results:
                chunk_data = dict(result['c'])
                entities = result['entities']
                
                # Calculate relevance score based on query match in text
                text = chunk_data.get('text', '').lower()
                query_lower = query.lower()
                
                # Simple relevance scoring
                if query_lower in text:
                    position = text.find(query_lower)
                    # Earlier mention = higher score
                    score = max(0.3, 1.0 - (position / len(text)) * 0.5)
                else:
                    score = 0.2
                
                retrieval_result = RetrievalResult(
                    id=chunk_data.get('id', str(uuid.uuid4())),
                    type=ResultType.CHUNK,
                    content=chunk_data.get('text', ''),
                    metadata=self._clean_node_properties(chunk_data),
                    score=score,
                    source="neo4j.text_content",
                    timestamp=self._parse_timestamp(chunk_data.get('created_at')),
                    entities=entities if entities[0].get('name') else []
                )
                
                retrieval_results.append(retrieval_result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Text content search failed: {e}")
            return []
    
    async def _search_relationship_paths(self, 
                                        query: str, 
                                        depth: int,
                                        relationship_types: List[str],
                                        user_id: str,
                                        limit: int) -> List[RetrievalResult]:
        """Search for interesting relationship paths containing the query terms."""
        try:
            # This is a more exploratory search for relationship patterns
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            user_filter = "AND c.user_id = $user_id" if user_id else ""
            
            path_query = f"""
            MATCH (c:AudioChunk)-[:MENTIONS]->(e1)-[r{rel_filter}*1..{min(depth, 3)}]-(e2)<-[:MENTIONS]-(c2:AudioChunk)
            WHERE (c.text =~ $text_pattern OR c2.text =~ $text_pattern OR 
                   e1.name =~ $entity_pattern OR e2.name =~ $entity_pattern)
            {user_filter.replace('AND', 'WHERE') if not user_id else user_filter}
            AND c <> c2
            WITH c, c2, e1, e2, size([rel in r WHERE type(rel) <> 'MENTIONS']) as path_length
            RETURN DISTINCT c, e1.name as start_entity, e2.name as end_entity, path_length
            ORDER BY path_length ASC
            LIMIT $limit
            """
            
            params = {
                "text_pattern": f"(?i).*{query}.*",
                "entity_pattern": f"(?i).*{query}.*",
                "limit": limit
            }
            
            if user_id:
                params["user_id"] = user_id
            
            results = await self.neo4j_client.execute_read_query(path_query, params)
            
            retrieval_results = []
            for result in results:
                chunk_data = dict(result['c'])
                start_entity = result['start_entity']
                end_entity = result['end_entity']
                path_length = result['path_length']
                
                # Score based on path length (shorter paths are more relevant)
                score = max(0.2, 1.0 / (path_length + 1))
                
                retrieval_result = RetrievalResult(
                    id=chunk_data.get('id', str(uuid.uuid4())),
                    type=ResultType.CHUNK,
                    content=chunk_data.get('text', ''),
                    metadata={
                        **self._clean_node_properties(chunk_data),
                        'path_length': path_length,
                        'start_entity': start_entity,
                        'end_entity': end_entity
                    },
                    score=score,
                    source=f"neo4j.relationship_paths",
                    timestamp=self._parse_timestamp(chunk_data.get('created_at')),
                    relationships=[{
                        'from': start_entity,
                        'to': end_entity,
                        'path_length': path_length
                    }]
                )
                
                retrieval_results.append(retrieval_result)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Relationship path search failed: {e}")
            return []
    
    def _apply_additional_filters(self, 
                                 results: List[RetrievalResult], 
                                 filters: List[RetrievalFilter]) -> List[RetrievalResult]:
        """Apply filters that couldn't be handled in Neo4j queries directly."""
        filtered_results = results
        
        for filter in filters:
            filtered_results = self._apply_single_filter(filtered_results, filter)
        
        return filtered_results
    
    def _rank_graph_results(self, results: List[RetrievalResult], query: str) -> List[RetrievalResult]:
        """Rank results based on graph-specific relevance factors."""
        def graph_score(result: RetrievalResult) -> float:
            base_score = result.score
            
            # Boost results with more relationships
            relationship_boost = len(result.relationships) * 0.1
            
            # Boost results with more entities
            entity_boost = len(result.entities) * 0.05
            
            # Boost chunks over entities for general search
            type_boost = 0.1 if result.type == ResultType.CHUNK else 0.0
            
            # Boost results from entity mentions over text content
            source_boost = 0.1 if "entity_mentions" in result.source else 0.0
            
            total_score = base_score + relationship_boost + entity_boost + type_boost + source_boost
            return min(1.0, total_score)
        
        # Sort by enhanced score
        return sorted(results, key=graph_score, reverse=True)
    
    def _clean_node_properties(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize node properties from Neo4j."""
        cleaned = {}
        
        # Standard field mappings
        field_mappings = {
            'id': 'node_id',
            'audio_id': 'audio_id',
            'user_id': 'user_id',
            'chunk_index': 'chunk_index',
            'text': 'content',
            'name': 'entity_name',
            'normalized_name': 'normalized_name',
            'type': 'entity_type',
            'mention_count': 'mention_count',
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }
        
        for old_key, new_key in field_mappings.items():
            if old_key in node_data and node_data[old_key] is not None:
                cleaned[new_key] = node_data[old_key]
        
        # Add any additional properties not in the mapping
        for key, value in node_data.items():
            if key not in field_mappings and key not in cleaned and value is not None:
                cleaned[key] = value
        
        return cleaned
    
    def _parse_timestamp(self, timestamp_data: Any) -> datetime:
        """Parse timestamp from Neo4j datetime or string."""
        if not timestamp_data:
            return datetime.utcnow()
        
        try:
            if hasattr(timestamp_data, 'to_native'):
                # Neo4j DateTime object
                return timestamp_data.to_native()
            elif isinstance(timestamp_data, str):
                # String timestamp
                from dateutil.parser import parse
                return parse(timestamp_data)
            elif hasattr(timestamp_data, 'isoformat'):
                # Already a datetime
                return timestamp_data
            else:
                return datetime.utcnow()
                
        except Exception:
            logger.warning(f"Failed to parse timestamp: {timestamp_data}")
            return datetime.utcnow()
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Neo4j graph."""
        if not self._initialized:
            await self.initialize()
        
        try:
            stats_query = """
            MATCH (c:AudioChunk) WITH count(c) as chunks
            MATCH (e) WHERE NOT e:AudioChunk WITH count(e) as entities, chunks
            MATCH ()-[r]->() WITH count(r) as relationships, entities, chunks
            RETURN chunks, entities, relationships
            """
            
            result = await self.neo4j_client.execute_read_query(stats_query, {})
            
            if result:
                stats = result[0]
                return {
                    "retriever": self.name,
                    "chunks": stats.get("chunks", 0),
                    "entities": stats.get("entities", 0),
                    "relationships": stats.get("relationships", 0),
                    "default_depth": self.default_depth,
                    "max_depth": self.max_depth
                }
            
            return {"error": "No data found"}
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Neo4j retriever."""
        base_health = await super().health_check()
        
        if not self._initialized:
            return {**base_health, "neo4j_status": "not_initialized"}
        
        try:
            # Check Neo4j client health
            client_health = await self.neo4j_client.health_check()
            
            # Get graph statistics
            graph_stats = await self.get_graph_statistics()
            
            return {
                **base_health,
                "neo4j_status": "healthy",
                "client_health": client_health,
                "graph_statistics": graph_stats,
                "default_depth": self.default_depth,
                "max_depth": self.max_depth
            }
            
        except Exception as e:
            return {
                **base_health,
                "neo4j_status": "unhealthy",
                "error": str(e)
            }