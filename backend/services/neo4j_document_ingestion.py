"""
Neo4j document ingestion strategy for building knowledge graphs.
Implements the strategy described in the architecture evolution document.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from neo4j import GraphDatabase
from core.config import settings
from services.ner_service import NERService

logger = logging.getLogger(__name__)


class Neo4jDocumentIngestion:
    """Neo4j document ingestion for knowledge graph construction."""
    
    def __init__(self):
        """Initialize Neo4j document ingestion service."""
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.ner_service = NERService()
        logger.info("Neo4j Document Ingestion service initialized")
    
    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def ingest_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """
        Ingest a document into Neo4j knowledge graph.
        
        Args:
            doc_id: Unique document identifier
            content: Document content/transcript
            metadata: Document metadata (audio_id, timestamp, etc.)
            user_id: Optional user ID for data isolation
            
        Returns:
            Success status
        """
        try:
            with self.driver.session() as session:
                # Extract entities from content
                entities = self.ner_service.extract_entities(content)
                
                # Extract document metadata
                audio_id = metadata.get('audio_id', '')
                timestamp = metadata.get('timestamp', datetime.utcnow().isoformat())
                language = metadata.get('language', 'unknown')
                category = metadata.get('category', 'transcript')
                
                # Ingest document and related entities
                session.execute_write(
                    self._create_document_transaction,
                    doc_id=doc_id,
                    content=content,
                    audio_id=audio_id,
                    timestamp=timestamp,
                    language=language,
                    category=category,
                    user_id=user_id,
                    entities=entities
                )
                
                logger.info(f"Successfully ingested document {doc_id} with {len(entities)} entities")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ingest document {doc_id}: {e}")
            return False
    
    def _create_document_transaction(
        self,
        tx,
        doc_id: str,
        content: str,
        audio_id: str,
        timestamp: str,
        language: str,
        category: str,
        user_id: Optional[str],
        entities: List[Dict[str, Any]]
    ):
        """
        Transaction to create document and its relationships.
        
        This implements the knowledge graph strategy described in the architecture document.
        """
        # Create or update the document node
        query = """
        MERGE (d:Document {id: $doc_id})
        SET d.content = $content,
            d.audio_id = $audio_id,
            d.timestamp = $timestamp,
            d.language = $language,
            d.category = $category,
            d.user_id = $user_id,
            d.updated_at = datetime()
        """
        tx.run(query, {
            'doc_id': doc_id,
            'content': content,
            'audio_id': audio_id,
            'timestamp': timestamp,
            'language': language,
            'category': category,
            'user_id': user_id
        })
        
        # Process entities and create relationships
        for entity in entities:
            entity_text = entity.get('text', '').strip()
            entity_type = entity.get('type', 'MISC')
            confidence = entity.get('confidence', 0.0)
            
            if not entity_text:
                continue
            
            # Create entity node and relationship to document
            self._create_entity_relationship(
                tx, doc_id, entity_text, entity_type, confidence
            )
        
        # Extract topics/themes (simplified approach)
        topics = self._extract_topics(content)
        for topic in topics:
            self._create_topic_relationship(tx, doc_id, topic)
    
    def _create_entity_relationship(
        self,
        tx,
        doc_id: str,
        entity_text: str,
        entity_type: str,
        confidence: float
    ):
        """Create entity and its relationship to document."""
        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (e:Entity {name: $entity_text, type: $entity_type})
        MERGE (d)-[r:MENTIONS]->(e)
        SET r.confidence = $confidence,
            r.created_at = datetime()
        """
        tx.run(query, {
            'doc_id': doc_id,
            'entity_text': entity_text,
            'entity_type': entity_type,
            'confidence': confidence
        })
        
        # Create specific entity type relationships
        if entity_type == 'PERSON':
            self._create_person_node(tx, entity_text)
        elif entity_type == 'ORG':
            self._create_organization_node(tx, entity_text)
        elif entity_type == 'LOC':
            self._create_location_node(tx, entity_text)
    
    def _create_person_node(self, tx, person_name: str):
        """Create or update a person node."""
        query = """
        MERGE (p:Person {name: $person_name})
        SET p.updated_at = datetime()
        """
        tx.run(query, {'person_name': person_name})
    
    def _create_organization_node(self, tx, org_name: str):
        """Create or update an organization node."""
        query = """
        MERGE (o:Organization {name: $org_name})
        SET o.updated_at = datetime()
        """
        tx.run(query, {'org_name': org_name})
    
    def _create_location_node(self, tx, location_name: str):
        """Create or update a location node."""
        query = """
        MERGE (l:Location {name: $location_name})
        SET l.updated_at = datetime()
        """
        tx.run(query, {'location_name': location_name})
    
    def _create_topic_relationship(self, tx, doc_id: str, topic: str):
        """Create topic and its relationship to document."""
        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (t:Topic {name: $topic})
        MERGE (d)-[r:DISCUSSES]->(t)
        SET r.created_at = datetime()
        """
        tx.run(query, {
            'doc_id': doc_id,
            'topic': topic
        })
    
    def _extract_topics(self, content: str) -> List[str]:
        """
        Extract topics/themes from content.
        
        This is a simplified implementation. In production, you might use:
        - Topic modeling (LDA, BERTopic)
        - Keyword extraction
        - LLM-based topic extraction
        """
        # Simple keyword-based topic extraction
        keywords = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'business', 'strategy', 'marketing', 'sales',
            'technology', 'software', 'development', 'programming',
            'health', 'medical', 'healthcare',
            'finance', 'money', 'investment', 'economics',
            'education', 'learning', 'training',
            'research', 'science', 'innovation'
        ]
        
        content_lower = content.lower()
        found_topics = []
        
        for keyword in keywords:
            if keyword in content_lower:
                found_topics.append(keyword.title())
        
        return found_topics[:5]  # Limit to top 5 topics
    
    def create_entity_relationships(self, doc_id: str) -> bool:
        """
        Create relationships between entities mentioned in the same document.
        
        This creates co-occurrence relationships that can be useful for
        understanding entity connections.
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (d:Document {id: $doc_id})-[:MENTIONS]->(e1:Entity)
                MATCH (d)-[:MENTIONS]->(e2:Entity)
                WHERE e1 <> e2 AND e1.name < e2.name
                MERGE (e1)-[r:CO_OCCURS_WITH]-(e2)
                SET r.document_count = coalesce(r.document_count, 0) + 1,
                    r.last_seen = datetime()
                """
                session.run(query, {'doc_id': doc_id})
                return True
                
        except Exception as e:
            logger.error(f"Failed to create entity relationships for {doc_id}: {e}")
            return False
    
    def find_related_documents(
        self,
        doc_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find documents related to the given document based on shared entities.
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (d1:Document {id: $doc_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(d2:Document)
                WHERE d1 <> d2
                WITH d2, count(e) as shared_entities
                ORDER BY shared_entities DESC
                LIMIT $limit
                RETURN d2.id as doc_id, d2.audio_id as audio_id, 
                       d2.timestamp as timestamp, shared_entities
                """
                result = session.run(query, {'doc_id': doc_id, 'limit': limit})
                
                related_docs = []
                for record in result:
                    related_docs.append({
                        'doc_id': record['doc_id'],
                        'audio_id': record['audio_id'],
                        'timestamp': record['timestamp'],
                        'shared_entities': record['shared_entities']
                    })
                
                return related_docs
                
        except Exception as e:
            logger.error(f"Failed to find related documents for {doc_id}: {e}")
            return []
    
    def get_entity_network(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get the network of entities connected to the given entity.
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH path = (e1:Entity {name: $entity_name})-[:CO_OCCURS_WITH*1..$depth]-(e2:Entity)
                RETURN path
                LIMIT 100
                """
                result = session.run(query, {'entity_name': entity_name, 'depth': depth})
                
                nodes = set()
                edges = []
                
                for record in result:
                    path = record['path']
                    path_nodes = path.nodes
                    path_relationships = path.relationships
                    
                    # Add nodes
                    for node in path_nodes:
                        nodes.add(node['name'])
                    
                    # Add edges
                    for rel in path_relationships:
                        start_node = rel.start_node['name']
                        end_node = rel.end_node['name']
                        edges.append({
                            'source': start_node,
                            'target': end_node,
                            'document_count': rel.get('document_count', 1)
                        })
                
                return {
                    'nodes': list(nodes),
                    'edges': edges,
                    'center': entity_name
                }
                
        except Exception as e:
            logger.error(f"Failed to get entity network for {entity_name}: {e}")
            return {'nodes': [], 'edges': [], 'center': entity_name}
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get statistics about the ingested knowledge graph."""
        try:
            with self.driver.session() as session:
                # Count nodes by type
                node_counts = {}
                for node_type in ['Document', 'Entity', 'Person', 'Organization', 'Location', 'Topic']:
                    query = f"MATCH (n:{node_type}) RETURN count(n) as count"
                    result = session.run(query)
                    node_counts[node_type.lower()] = result.single()['count']
                
                # Count relationships
                rel_query = "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count"
                result = session.run(rel_query)
                rel_counts = {record['rel_type']: record['count'] for record in result}
                
                return {
                    'nodes': node_counts,
                    'relationships': rel_counts,
                    'total_nodes': sum(node_counts.values()),
                    'total_relationships': sum(rel_counts.values())
                }
                
        except Exception as e:
            logger.error(f"Failed to get ingestion stats: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Check Neo4j connection and ingestion service health."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
                
                stats = self.get_ingestion_stats()
                
                return {
                    'status': 'healthy',
                    'neo4j_connected': True,
                    'stats': stats
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'neo4j_connected': False,
                'error': str(e)
            }