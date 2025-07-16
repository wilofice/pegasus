"""Factory for creating Context Aggregator V2 instances with real services."""
import logging
from typing import Optional

from services.context_aggregator_v2 import ContextAggregatorV2, AggregationConfig
from services.context_ranker import ContextRanker, RankingWeights, RankingStrategy
from services.retrieval.qdrant_retriever import QdrantRetriever
from services.retrieval.neo4j_retriever import Neo4jRetriever

logger = logging.getLogger(__name__)


class ContextAggregatorFactory:
    """Factory for creating and configuring Context Aggregator V2 instances."""
    
    @staticmethod
    async def create_default_aggregator(
        qdrant_collection: str = "audio_transcripts",
        qdrant_similarity_threshold: float = 0.1,
        neo4j_default_depth: int = 2,
        neo4j_max_depth: int = 5,
        ranking_strategy: RankingStrategy = RankingStrategy.ENSEMBLE,
        ranking_weights: Optional[RankingWeights] = None
    ) -> ContextAggregatorV2:
        """Create a Context Aggregator V2 with default real services.
        
        Args:
            qdrant_collection: Qdrant collection name
            qdrant_similarity_threshold: Minimum similarity threshold for Qdrant
            neo4j_default_depth: Default traversal depth for Neo4j
            neo4j_max_depth: Maximum traversal depth for Neo4j
            ranking_strategy: Default ranking strategy to use
            ranking_weights: Custom ranking weights (uses defaults if None)
            
        Returns:
            Configured ContextAggregatorV2 instance
        """
        try:
            logger.info("Creating Context Aggregator V2 with real services...")
            
            # Create Qdrant Retriever
            qdrant_retriever = QdrantRetriever()
            
            # Create Neo4j Retriever
            neo4j_retriever = Neo4jRetriever(
                default_depth=neo4j_default_depth,
                max_depth=neo4j_max_depth
            )
            
            # Create Context Ranker
            context_ranker = ContextRanker(
                default_weights=ranking_weights,
                strategy=ranking_strategy
            )
            
            # Create default aggregation configuration
            default_config = AggregationConfig(
                ranking_strategy=ranking_strategy,
                ranking_weights=ranking_weights
            )
            
            # Create aggregator
            aggregator = ContextAggregatorV2(
                qdrant_retriever=qdrant_retriever,
                neo4j_retriever=neo4j_retriever,
                context_ranker=context_ranker,
                default_config=default_config
            )
            
            logger.info("Context Aggregator V2 created successfully")
            return aggregator
            
        except Exception as e:
            logger.error(f"Failed to create Context Aggregator V2: {e}")
            raise
    
    @staticmethod
    async def create_optimized_aggregator(
        optimization_profile: str = "balanced"
    ) -> ContextAggregatorV2:
        """Create an optimized Context Aggregator V2 for specific use cases.
        
        Args:
            optimization_profile: Optimization profile ('speed', 'accuracy', 'balanced')
            
        Returns:
            Optimized ContextAggregatorV2 instance
        """
        try:
            if optimization_profile == "speed":
                # Optimized for fast response times
                return await ContextAggregatorFactory.create_default_aggregator(
                    qdrant_similarity_threshold=0.2,  # Higher threshold for fewer results
                    neo4j_default_depth=1,  # Shallow graph traversal
                    neo4j_max_depth=3,
                    ranking_strategy=RankingStrategy.HYBRID,  # Simpler ranking
                    ranking_weights=RankingWeights(
                        semantic_similarity=0.6,  # Favor fast vector search
                        graph_centrality=0.2,
                        recency=0.1,
                        entity_overlap=0.1
                    )
                )
                
            elif optimization_profile == "accuracy":
                # Optimized for comprehensive and accurate results
                return await ContextAggregatorFactory.create_default_aggregator(
                    qdrant_similarity_threshold=0.05,  # Lower threshold for more results
                    neo4j_default_depth=3,  # Deeper graph traversal
                    neo4j_max_depth=6,
                    ranking_strategy=RankingStrategy.ENSEMBLE,  # Most sophisticated ranking
                    ranking_weights=RankingWeights(
                        semantic_similarity=0.35,
                        graph_centrality=0.35,  # Equal weight to graph and vector
                        recency=0.2,
                        entity_overlap=0.1
                    )
                )
                
            else:  # balanced
                # Default balanced configuration
                return await ContextAggregatorFactory.create_default_aggregator()
                
        except Exception as e:
            logger.error(f"Failed to create optimized aggregator: {e}")
            raise
    
    @staticmethod
    async def create_custom_aggregator(
        qdrant_config: dict,
        neo4j_config: dict,
        ranking_config: dict,
        aggregation_config: dict
    ) -> ContextAggregatorV2:
        """Create a fully customized Context Aggregator V2.
        
        Args:
            qdrant_config: Qdrant retriever configuration
            neo4j_config: Neo4j retriever configuration  
            ranking_config: Context ranker configuration
            aggregation_config: Aggregation configuration
            
        Returns:
            Customized ContextAggregatorV2 instance
        """
        try:
            # Create Qdrant Retriever with custom config
            qdrant_retriever = QdrantRetriever()
            
            # Create Neo4j Retriever with custom config
            neo4j_retriever = Neo4jRetriever(**neo4j_config)
            
            # Create Context Ranker with custom config
            ranking_weights = None
            if 'weights' in ranking_config:
                ranking_weights = RankingWeights(**ranking_config['weights'])
            
            context_ranker = ContextRanker(
                default_weights=ranking_weights,
                strategy=ranking_config.get('strategy', RankingStrategy.ENSEMBLE)
            )
            
            # Create aggregation config
            if 'ranking_weights' in aggregation_config and ranking_weights:
                aggregation_config['ranking_weights'] = ranking_weights
            
            default_config = AggregationConfig(**aggregation_config)
            
            # Create aggregator
            aggregator = ContextAggregatorV2(
                qdrant_retriever=qdrant_retriever,
                neo4j_retriever=neo4j_retriever,
                context_ranker=context_ranker,
                default_config=default_config
            )
            
            logger.info("Custom Context Aggregator V2 created successfully")
            return aggregator
            
        except Exception as e:
            logger.error(f"Failed to create custom aggregator: {e}")
            raise


# Convenience function for easy access
async def get_context_aggregator(profile: str = "balanced") -> ContextAggregatorV2:
    """Get a Context Aggregator V2 instance with specified optimization profile.
    
    Args:
        profile: Optimization profile ('speed', 'accuracy', 'balanced', 'default')
        
    Returns:
        ContextAggregatorV2 instance
    """
    if profile == "default":
        return await ContextAggregatorFactory.create_default_aggregator()
    else:
        return await ContextAggregatorFactory.create_optimized_aggregator(profile)