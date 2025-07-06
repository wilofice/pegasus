"""Modern Context Aggregator Service integrating retrieval services and ranking algorithm."""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from services.retrieval.chromadb_retriever import ChromaDBRetriever
from services.retrieval.neo4j_retriever import Neo4jRetriever
from services.retrieval.base import BaseRetriever, RetrievalResult, RetrievalFilter, ResultType
from services.context_ranker import ContextRanker, RankingStrategy, RankingWeights, RankedResult

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Available context aggregation strategies."""
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"
    ENSEMBLE = "ensemble"
    ADAPTIVE = "adaptive"
    GRAPH_TRAVERSAL = "graph_traversal"


@dataclass
class AggregationConfig:
    """Configuration for context aggregation."""
    strategy: AggregationStrategy = AggregationStrategy.HYBRID
    max_results: int = 20
    vector_weight: float = 0.7
    graph_weight: float = 0.3
    
    # Retrieval settings
    include_related: bool = True
    deduplication_enabled: bool = True
    similarity_threshold: float = 0.1
    
    # Ranking settings
    ranking_strategy: RankingStrategy = RankingStrategy.ENSEMBLE
    ranking_weights: Optional[RankingWeights] = None
    
    # Performance settings
    timeout_seconds: float = 30.0
    parallel_retrieval: bool = True

    # Graph Traversal settings
    traversal_depth: int = 2


@dataclass
class AggregationMetrics:
    """Metrics from context aggregation process."""
    total_retrieval_time_ms: float
    total_ranking_time_ms: float
    total_processing_time_ms: float
    vector_results_count: int
    graph_results_count: int
    final_results_count: int
    duplicates_removed: int
    strategy_used: str
    ranking_strategy_used: str


@dataclass
class AggregatedContext:
    """Final aggregated context with ranked results."""
    results: List[RankedResult]
    query: str
    config: AggregationConfig
    metrics: AggregationMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_top_results(self, limit: int = 10) -> List[RankedResult]:
        """Get top N results by unified score."""
        return self.results[:limit]
    
    def get_results_by_source(self, source_type: str) -> List[RankedResult]:
        """Get results from specific source type."""
        return [r for r in self.results if r.source_type == source_type]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of aggregated results."""
        if not self.results:
            return {"total_results": 0}
        
        scores = [r.unified_score for r in self.results]
        source_counts = {}
        for result in self.results:
            source_counts[result.source_type] = source_counts.get(result.source_type, 0) + 1
        
        return {
            "total_results": len(self.results),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "source_distribution": source_counts,
            "processing_time_ms": self.metrics.total_processing_time_ms,
            "strategy": self.config.strategy.value
        }


class ContextAggregatorV2:
    """Modern context aggregator with retrieval service and ranking integration."""
    
    def __init__(self,
                 chromadb_retriever: ChromaDBRetriever,
                 neo4j_retriever: Neo4jRetriever,
                 context_ranker: ContextRanker,
                 default_config: Optional[AggregationConfig] = None):
        """Initialize context aggregator."""
        self.chromadb_retriever = chromadb_retriever
        self.neo4j_retriever = neo4j_retriever
        self.context_ranker = context_ranker
        self.default_config = default_config or AggregationConfig()
        
        from services.ner_service import NERService
        self.ner_service = NERService()

        logger.info("Context Aggregator V2 initialized with modern retrieval services")
    
    async def aggregate_context(self,
                               query: str,
                               config: Optional[AggregationConfig] = None,
                               user_id: Optional[str] = None,
                               filters: Optional[List[RetrievalFilter]] = None,
                               **kwargs) -> AggregatedContext:
        """Aggregate context from multiple sources with unified ranking.
        
        Args:
            query: Search query
            config: Aggregation configuration
            user_id: User ID for data isolation
            filters: Additional retrieval filters
            **kwargs: Additional parameters for retrievers
            
        Returns:
            AggregatedContext with ranked results
        """
        start_time = datetime.now()
        config = config or self.default_config
        
        try:
            logger.info(f"Starting context aggregation for query: '{query[:50]}...'")
            
            # Initialize metrics
            metrics = AggregationMetrics(
                total_retrieval_time_ms=0,
                total_ranking_time_ms=0,
                total_processing_time_ms=0,
                vector_results_count=0,
                graph_results_count=0,
                final_results_count=0,
                duplicates_removed=0,
                strategy_used=config.strategy.value,
                ranking_strategy_used=config.ranking_strategy.value
            )
            
            # Retrieve results based on strategy
            retrieval_start = datetime.now()
            
            if config.strategy == AggregationStrategy.VECTOR_ONLY:
                all_results = await self._vector_only_retrieval(query, config, user_id, filters, **kwargs)
            elif config.strategy == AggregationStrategy.GRAPH_ONLY:
                all_results = await self._graph_only_retrieval(query, config, user_id, filters, **kwargs)
            elif config.strategy == AggregationStrategy.HYBRID:
                all_results = await self._hybrid_retrieval(query, config, user_id, filters, **kwargs)
            elif config.strategy == AggregationStrategy.ENSEMBLE:
                all_results = await self._ensemble_retrieval(query, config, user_id, filters, **kwargs)
            elif config.strategy == AggregationStrategy.ADAPTIVE:
                all_results = await self._adaptive_retrieval(query, config, user_id, filters, **kwargs)
            elif config.strategy == AggregationStrategy.GRAPH_TRAVERSAL:
                all_results = await self._graph_traversal_retrieval(query, config, user_id, filters, **kwargs)
            else:
                raise ValueError(f"Unknown aggregation strategy: {config.strategy}")
            
            retrieval_time = (datetime.now() - retrieval_start).total_seconds() * 1000
            metrics.total_retrieval_time_ms = retrieval_time
            
            # Count results by source
            metrics.vector_results_count = len([r for r in all_results if 'chromadb' in r.source.lower()])
            metrics.graph_results_count = len([r for r in all_results if 'neo4j' in r.source.lower()])
            
            # Apply deduplication if enabled
            if config.deduplication_enabled:
                dedupe_count_before = len(all_results)
                all_results = self._deduplicate_results(all_results)
                metrics.duplicates_removed = dedupe_count_before - len(all_results)
            
            # Apply ranking
            ranking_start = datetime.now()
            ranked_results = self.context_ranker.rank_results(
                results=all_results,
                query=query,
                strategy=config.ranking_strategy,
                weights=config.ranking_weights,
                context={"user_id": user_id, "aggregation_strategy": config.strategy.value}
            )
            ranking_time = (datetime.now() - ranking_start).total_seconds() * 1000
            metrics.total_ranking_time_ms = ranking_time
            
            # Limit final results
            final_results = ranked_results[:config.max_results]
            metrics.final_results_count = len(final_results)
            
            # Calculate total processing time
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            metrics.total_processing_time_ms = total_time
            
            # Create aggregated context
            aggregated_context = AggregatedContext(
                results=final_results,
                query=query,
                config=config,
                metrics=metrics,
                metadata={
                    "user_id": user_id,
                    "timestamp": start_time.isoformat(),
                    "filters_applied": len(filters) if filters else 0,
                    "retrievers_used": self._get_retrievers_used(config.strategy)
                }
            )
            
            logger.info(f"Context aggregation completed: {len(final_results)} results in {total_time:.1f}ms")
            return aggregated_context
            
        except Exception as e:
            logger.error(f"Context aggregation failed: {e}")
            # Return empty context with error information
            error_metrics = AggregationMetrics(
                total_retrieval_time_ms=0,
                total_ranking_time_ms=0,
                total_processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                vector_results_count=0,
                graph_results_count=0,
                final_results_count=0,
                duplicates_removed=0,
                strategy_used=config.strategy.value,
                ranking_strategy_used=config.ranking_strategy.value
            )
            
            return AggregatedContext(
                results=[],
                query=query,
                config=config,
                metrics=error_metrics,
                metadata={"error": str(e), "timestamp": start_time.isoformat()}
            )
    
    async def _vector_only_retrieval(self,
                                   query: str,
                                   config: AggregationConfig,
                                   user_id: Optional[str],
                                   filters: Optional[List[RetrievalFilter]],
                                   **kwargs) -> List[RetrievalResult]:
        """Perform vector-only retrieval."""
        try:
            if not self.chromadb_retriever._initialized:
                await self.chromadb_retriever.initialize()
            
            results = await self.chromadb_retriever.search(
                query=query,
                filters=filters,
                limit=config.max_results,
                user_id=user_id,
                **kwargs
            )
            
            logger.debug(f"Vector-only retrieval: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector-only retrieval failed: {e}")
            return []
    
    async def _graph_only_retrieval(self,
                                  query: str,
                                  config: AggregationConfig,
                                  user_id: Optional[str],
                                  filters: Optional[List[RetrievalFilter]],
                                  **kwargs) -> List[RetrievalResult]:
        """Perform graph-only retrieval."""
        try:
            if not self.neo4j_retriever._initialized:
                await self.neo4j_retriever.initialize()
            
            results = await self.neo4j_retriever.search(
                query=query,
                filters=filters,
                limit=config.max_results,
                user_id=user_id,
                **kwargs
            )
            
            logger.debug(f"Graph-only retrieval: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Graph-only retrieval failed: {e}")
            return []
    
    async def _hybrid_retrieval(self,
                              query: str,
                              config: AggregationConfig,
                              user_id: Optional[str],
                              filters: Optional[List[RetrievalFilter]],
                              **kwargs) -> List[RetrievalResult]:
        """Perform hybrid retrieval combining vector and graph."""
        try:
            # Calculate result limits for each retriever
            vector_limit = int(config.max_results * config.vector_weight * 1.5)  # Get extra for better selection
            graph_limit = int(config.max_results * config.graph_weight * 1.5)
            
            if config.parallel_retrieval:
                # Parallel retrieval
                tasks = []
                
                if not self.chromadb_retriever._initialized:
                    tasks.append(self.chromadb_retriever.initialize())
                if not self.neo4j_retriever._initialized:
                    tasks.append(self.neo4j_retriever.initialize())
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Perform searches in parallel
                vector_task = self.chromadb_retriever.search(
                    query=query, filters=filters, limit=vector_limit, user_id=user_id, **kwargs
                )
                graph_task = self.neo4j_retriever.search(
                    query=query, filters=filters, limit=graph_limit, user_id=user_id, **kwargs
                )
                
                vector_results, graph_results = await asyncio.gather(
                    vector_task, graph_task, return_exceptions=True
                )
                
                # Handle exceptions
                if isinstance(vector_results, Exception):
                    logger.error(f"Vector search failed: {vector_results}")
                    vector_results = []
                if isinstance(graph_results, Exception):
                    logger.error(f"Graph search failed: {graph_results}")
                    graph_results = []
                    
            else:
                # Sequential retrieval
                if not self.chromadb_retriever._initialized:
                    await self.chromadb_retriever.initialize()
                vector_results = await self.chromadb_retriever.search(
                    query=query, filters=filters, limit=vector_limit, user_id=user_id, **kwargs
                )
                
                if not self.neo4j_retriever._initialized:
                    await self.neo4j_retriever.initialize()
                graph_results = await self.neo4j_retriever.search(
                    query=query, filters=filters, limit=graph_limit, user_id=user_id, **kwargs
                )
            
            # Combine results
            all_results = vector_results + graph_results
            
            logger.debug(f"Hybrid retrieval: {len(vector_results)} vector + {len(graph_results)} graph = {len(all_results)} total")
            return all_results
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            return []
    
    async def _ensemble_retrieval(self,
                                query: str,
                                config: AggregationConfig,
                                user_id: Optional[str],
                                filters: Optional[List[RetrievalFilter]],
                                **kwargs) -> List[RetrievalResult]:
        """Perform ensemble retrieval with multiple search strategies."""
        try:
            # Get base hybrid results
            hybrid_results = await self._hybrid_retrieval(query, config, user_id, filters, **kwargs)
            
            # Add specialized searches
            additional_results = []
            
            # Entity-focused search in Neo4j
            if config.include_related:
                try:
                    entity_results = await self.neo4j_retriever.find_entity_mentions(
                        entity_name=query,
                        user_id=user_id,
                        limit=max(5, config.max_results // 4)
                    )
                    additional_results.extend(entity_results)
                except Exception as e:
                    logger.warning(f"Entity search failed: {e}")
            
            # Combine all results
            all_results = hybrid_results + additional_results
            
            logger.debug(f"Ensemble retrieval: {len(hybrid_results)} hybrid + {len(additional_results)} additional = {len(all_results)} total")
            return all_results
            
        except Exception as e:
            logger.error(f"Ensemble retrieval failed: {e}")
            return []
    
    async def _adaptive_retrieval(self,
                                query: str,
                                config: AggregationConfig,
                                user_id: Optional[str],
                                filters: Optional[List[RetrievalFilter]],
                                **kwargs) -> List[RetrievalResult]:
        """Perform adaptive retrieval that adjusts strategy based on query analysis."""
        try:
            # Analyze query to determine best strategy
            query_analysis = self._analyze_query(query)
            
            # Adapt strategy based on query characteristics
            if query_analysis["has_entities"] and query_analysis["entity_count"] > 2:
                # Entity-heavy query: favor graph search
                adapted_config = AggregationConfig(
                    strategy=AggregationStrategy.HYBRID,
                    max_results=config.max_results,
                    vector_weight=0.4,
                    graph_weight=0.6,
                    include_related=True,
                    ranking_strategy=RankingStrategy.ENTITY_FOCUSED
                )
                logger.debug("Adaptive strategy: Entity-focused (graph-heavy)")
                
            elif query_analysis["is_semantic_query"]:
                # Semantic/conceptual query: favor vector search
                adapted_config = AggregationConfig(
                    strategy=AggregationStrategy.HYBRID,
                    max_results=config.max_results,
                    vector_weight=0.8,
                    graph_weight=0.2,
                    ranking_strategy=RankingStrategy.SEMANTIC_ONLY
                )
                logger.debug("Adaptive strategy: Semantic-focused (vector-heavy)")
                
            elif query_analysis["is_temporal_query"]:
                # Time-sensitive query: boost recency
                adapted_config = AggregationConfig(
                    strategy=AggregationStrategy.ENSEMBLE,
                    max_results=config.max_results,
                    vector_weight=config.vector_weight,
                    graph_weight=config.graph_weight,
                    ranking_strategy=RankingStrategy.TEMPORAL_BOOST
                )
                logger.debug("Adaptive strategy: Temporal-focused")
                
            else:
                # Default to ensemble for complex queries
                adapted_config = AggregationConfig(
                    strategy=AggregationStrategy.ENSEMBLE,
                    max_results=config.max_results,
                    vector_weight=config.vector_weight,
                    graph_weight=config.graph_weight,
                    ranking_strategy=RankingStrategy.ENSEMBLE
                )
                logger.debug("Adaptive strategy: Default ensemble")
            
            # Perform retrieval with adapted strategy
            if adapted_config.strategy == AggregationStrategy.ENSEMBLE:
                return await self._ensemble_retrieval(query, adapted_config, user_id, filters, **kwargs)
            else:
                return await self._hybrid_retrieval(query, adapted_config, user_id, filters, **kwargs)
                
        except Exception as e:
            logger.error(f"Adaptive retrieval failed: {e}")
            # Fallback to hybrid
            return await self._hybrid_retrieval(query, config, user_id, filters, **kwargs)
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query characteristics for adaptive strategy selection using NER."""
        try:
            entities = self.ner_service.extract_entities(query)
            entity_count = len(entities)
            entity_types = {e['type'] for e in entities}
            
            query_lower = query.lower()
            
            # More robust query classification
            is_semantic_query = any(k in query_lower for k in ['like', 'similar', 'about', 'concept'])
            is_complex_graph_query = entity_count > 1 and any(k in query_lower for k in ['relationship', 'connection', 'link', 'interaction'])

            return {
                "entities": entities,
                "entity_count": entity_count,
                "entity_types": entity_types,
                "is_semantic_query": is_semantic_query and entity_count == 0,
                "is_complex_graph_query": is_complex_graph_query,
                "query_length": len(query)
            }
            
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            return {
                "entities": [], "entity_count": 0, "entity_types": set(),
                "is_semantic_query": True, "is_complex_graph_query": False,
                "query_length": len(query)
            }
    
    async def _graph_traversal_retrieval(self,
                                      query: str,
                                      config: AggregationConfig,
                                      user_id: Optional[str],
                                      filters: Optional[List[RetrievalFilter]],
                                      **kwargs) -> List[RetrievalResult]:
        """Perform targeted graph traversal based on extracted entities."""
        try:
            query_analysis = self._analyze_query(query)
            entities = query_analysis['entities']

            if not entities:
                logger.warning("Graph traversal called without entities, falling back to hybrid.")
                return await self._hybrid_retrieval(query, config, user_id, filters, **kwargs)

            # Example: Find paths between two entities
            if len(entities) >= 2:
                entity1 = entities[0]['text']
                entity2 = entities[1]['text']
                logger.info(f"Performing graph traversal between '{entity1}' and '{entity2}'")
                
                return await self.neo4j_retriever.find_paths_between_entities(
                    entity1_name=entity1,
                    entity2_name=entity2,
                    max_depth=config.traversal_depth,
                    user_id=user_id
                )
            
            # Fallback for single entity
            return await self.neo4j_retriever.find_entity_mentions(
                entity_name=entities[0]['text'],
                user_id=user_id,
                limit=config.max_results
            )

        except Exception as e:
            logger.error(f"Graph traversal retrieval failed: {e}", exc_info=True)
            return []
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicate results based on content similarity."""
        if not results:
            return results
        
        try:
            # Group by ID first (exact duplicates)
            seen_ids = set()
            unique_results = []
            
            for result in results:
                if result.id not in seen_ids:
                    seen_ids.add(result.id)
                    unique_results.append(result)
            
            # TODO: Could add content-based deduplication here
            # For now, just remove exact ID duplicates
            
            logger.debug(f"Deduplication: {len(results)} -> {len(unique_results)} results")
            return unique_results
            
        except Exception as e:
            logger.warning(f"Deduplication failed: {e}")
            return results
    
    def _get_retrievers_used(self, strategy: AggregationStrategy) -> List[str]:
        """Get list of retrievers used for given strategy."""
        if strategy == AggregationStrategy.VECTOR_ONLY:
            return ["chromadb"]
        elif strategy == AggregationStrategy.GRAPH_ONLY:
            return ["neo4j"]
        else:
            return ["chromadb", "neo4j"]
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of context aggregator and dependencies."""
        try:
            health = {
                "service": "ContextAggregatorV2",
                "status": "healthy",
                "dependencies": {}
            }
            
            # Check retriever health
            try:
                chromadb_health = await self.chromadb_retriever.health_check()
                health["dependencies"]["chromadb_retriever"] = chromadb_health
            except Exception as e:
                health["dependencies"]["chromadb_retriever"] = {"status": "unhealthy", "error": str(e)}
            
            try:
                neo4j_health = await self.neo4j_retriever.health_check()
                health["dependencies"]["neo4j_retriever"] = neo4j_health
            except Exception as e:
                health["dependencies"]["neo4j_retriever"] = {"status": "unhealthy", "error": str(e)}
            
            try:
                ranker_health = await self.context_ranker.health_check()
                health["dependencies"]["context_ranker"] = ranker_health
            except Exception as e:
                health["dependencies"]["context_ranker"] = {"status": "unhealthy", "error": str(e)}
            
            # Overall health based on dependencies
            unhealthy_deps = [k for k, v in health["dependencies"].items() 
                            if v.get("status") != "healthy"]
            
            if unhealthy_deps:
                health["status"] = "degraded"
                health["unhealthy_dependencies"] = unhealthy_deps
            
            health["configuration"] = {
                "default_strategy": self.default_config.strategy.value,
                "default_max_results": self.default_config.max_results,
                "parallel_retrieval": self.default_config.parallel_retrieval
            }
            
            return health
            
        except Exception as e:
            return {
                "service": "ContextAggregatorV2",
                "status": "unhealthy",
                "error": str(e)
            }