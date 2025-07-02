"""Context ranking service for unified relevance scoring across multiple retrieval sources."""
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RankingStrategy(Enum):
    """Available ranking strategies."""
    SEMANTIC_ONLY = "semantic_only"
    STRUCTURAL_ONLY = "structural_only"
    HYBRID = "hybrid"
    ENSEMBLE = "ensemble"
    TEMPORAL_BOOST = "temporal_boost"
    ENTITY_FOCUSED = "entity_focused"


@dataclass
class RankingWeights:
    """Configurable weights for different ranking factors."""
    semantic_similarity: float = 0.4
    graph_centrality: float = 0.3
    recency: float = 0.2
    entity_overlap: float = 0.1
    content_quality: float = 0.0  # Optional additional factor
    
    def __post_init__(self):
        """Validate and normalize weights."""
        total = (self.semantic_similarity + self.graph_centrality + 
                self.recency + self.entity_overlap + self.content_quality)
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Ranking weights sum to {total:.3f}, normalizing to 1.0")
            # Normalize weights
            self.semantic_similarity /= total
            self.graph_centrality /= total
            self.recency /= total
            self.entity_overlap /= total
            self.content_quality /= total


@dataclass
class RankingFactor:
    """Individual ranking factor with score and explanation."""
    name: str
    score: float
    weight: float
    explanation: str
    raw_value: Optional[Any] = None


@dataclass 
class RankedResult:
    """A search result with unified ranking score and explanations."""
    id: str
    content: str
    source_type: str
    unified_score: float
    ranking_factors: List[RankingFactor] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Original source-specific scores
    semantic_score: Optional[float] = None
    structural_score: Optional[float] = None
    temporal_score: Optional[float] = None
    
    def get_explanation(self) -> Dict[str, Any]:
        """Get detailed explanation of ranking calculation."""
        return {
            "unified_score": self.unified_score,
            "factors": [
                {
                    "name": factor.name,
                    "score": factor.score,
                    "weight": factor.weight,
                    "contribution": factor.score * factor.weight,
                    "explanation": factor.explanation,
                    "raw_value": factor.raw_value
                }
                for factor in self.ranking_factors
            ],
            "source_scores": {
                "semantic": self.semantic_score,
                "structural": self.structural_score,
                "temporal": self.temporal_score
            }
        }


class ContextRanker:
    """Advanced context ranking service with multiple strategies and explainable scoring."""
    
    def __init__(self, 
                 default_weights: Optional[RankingWeights] = None,
                 strategy: RankingStrategy = RankingStrategy.ENSEMBLE):
        """Initialize context ranker.
        
        Args:
            default_weights: Default ranking weights configuration
            strategy: Default ranking strategy to use
        """
        self.default_weights = default_weights or RankingWeights()
        self.default_strategy = strategy
        
        logger.info(f"Context ranker initialized with strategy: {strategy.value}")
    
    def rank_results(self, 
                    results: List[Any], 
                    query: str = "",
                    strategy: Optional[RankingStrategy] = None,
                    weights: Optional[RankingWeights] = None,
                    context: Optional[Dict[str, Any]] = None) -> List[RankedResult]:
        """Rank a list of search results using specified strategy.
        
        Args:
            results: List of search results to rank (from retrievers)
            query: Original search query for context
            strategy: Ranking strategy to use
            weights: Custom ranking weights
            context: Additional context for ranking decisions
            
        Returns:
            List of RankedResult objects sorted by unified score
        """
        if not results:
            return []
        
        strategy = strategy or self.default_strategy
        weights = weights or self.default_weights
        context = context or {}
        
        logger.debug(f"Ranking {len(results)} results with strategy: {strategy.value}")
        
        try:
            # Convert results to unified format
            ranked_results = []
            
            for result in results:
                ranked_result = self._rank_single_result(
                    result, query, strategy, weights, context
                )
                if ranked_result:
                    ranked_results.append(ranked_result)
            
            # Sort by unified score
            ranked_results.sort(key=lambda r: r.unified_score, reverse=True)
            
            logger.debug(f"Ranking complete. Top score: {ranked_results[0].unified_score:.3f}")
            return ranked_results
            
        except Exception as e:
            logger.error(f"Error ranking results: {e}")
            return []
    
    def _rank_single_result(self, 
                           result: Any, 
                           query: str,
                           strategy: RankingStrategy,
                           weights: RankingWeights,
                           context: Dict[str, Any]) -> Optional[RankedResult]:
        """Rank a single result and return RankedResult."""
        try:
            # Extract common fields from different result types
            result_id = self._extract_field(result, ['id', 'chunk_id', '_id'])
            content = self._extract_field(result, ['content', 'text', 'document'])
            source_type = self._extract_field(result, ['source_type', 'source', 'retriever_type'], 'unknown')
            metadata = self._extract_field(result, ['metadata'], {})
            
            if not result_id or not content:
                logger.warning("Result missing required fields, skipping")
                return None
            
            # Calculate individual ranking factors
            factors = []
            
            # 1. Semantic Similarity Factor
            semantic_factor = self._calculate_semantic_factor(result, query, context)
            factors.append(semantic_factor)
            
            # 2. Graph Centrality/Structural Factor  
            structural_factor = self._calculate_structural_factor(result, context)
            factors.append(structural_factor)
            
            # 3. Recency Factor
            recency_factor = self._calculate_recency_factor(result, context)
            factors.append(recency_factor)
            
            # 4. Entity Overlap Factor
            entity_factor = self._calculate_entity_overlap_factor(result, query, context)
            factors.append(entity_factor)
            
            # 5. Content Quality Factor (if enabled)
            if weights.content_quality > 0:
                quality_factor = self._calculate_content_quality_factor(result, context)
                factors.append(quality_factor)
            
            # Apply strategy-specific modifications
            factors = self._apply_strategy_modifications(factors, strategy, result, context)
            
            # Calculate unified score
            unified_score = self._calculate_unified_score(factors, weights)
            
            # Create ranked result
            ranked_result = RankedResult(
                id=result_id,
                content=content,
                source_type=source_type,
                unified_score=unified_score,
                ranking_factors=factors,
                metadata=metadata,
                semantic_score=semantic_factor.score,
                structural_score=structural_factor.score,
                temporal_score=recency_factor.score
            )
            
            return ranked_result
            
        except Exception as e:
            logger.error(f"Error ranking single result: {e}")
            return None
    
    def _calculate_semantic_factor(self, result: Any, query: str, context: Dict[str, Any]) -> RankingFactor:
        """Calculate semantic similarity factor."""
        try:
            # Try to extract vector similarity scores
            vector_score = (
                self._extract_field(result, ['vector_similarity', 'similarity_score']) or
                self._extract_field(result, ['score']) or
                self._extract_field(result, ['distance'], transform=lambda d: 1.0 - d if d is not None else None)
            )
            
            if vector_score is not None:
                score = max(0.0, min(1.0, vector_score))
                explanation = f"Vector similarity: {score:.3f}"
                raw_value = vector_score
            else:
                # Fallback: simple text similarity
                content = self._extract_field(result, ['content', 'text', 'document'], '')
                score = self._calculate_text_similarity(query, content)
                explanation = f"Text-based similarity: {score:.3f}"
                raw_value = score
            
            return RankingFactor(
                name="semantic_similarity",
                score=score,
                weight=0.4,  # Will be overridden by weights
                explanation=explanation,
                raw_value=raw_value
            )
            
        except Exception as e:
            logger.warning(f"Error calculating semantic factor: {e}")
            return RankingFactor("semantic_similarity", 0.0, 0.4, "Error calculating similarity")
    
    def _calculate_structural_factor(self, result: Any, context: Dict[str, Any]) -> RankingFactor:
        """Calculate graph centrality/structural relevance factor."""
        try:
            # Try to extract graph-based scores
            graph_score = (
                self._extract_field(result, ['structural_relevance', 'graph_score']) or
                self._extract_field(result, ['centrality_score'])
            )
            
            if graph_score is not None:
                score = max(0.0, min(1.0, graph_score))
                explanation = f"Graph centrality: {score:.3f}"
                raw_value = graph_score
            else:
                # Fallback: entity-based structural scoring
                metadata = self._extract_field(result, ['metadata'], {})
                entity_count = metadata.get('entity_count', 0)
                related_entities = len(metadata.get('related_entities', []))
                
                # Simple structural score based on entity connections
                score = min(1.0, (entity_count + related_entities) / 10.0)
                explanation = f"Entity connections: {entity_count + related_entities}"
                raw_value = entity_count + related_entities
            
            return RankingFactor(
                name="graph_centrality",
                score=score,
                weight=0.3,
                explanation=explanation,
                raw_value=raw_value
            )
            
        except Exception as e:
            logger.warning(f"Error calculating structural factor: {e}")
            return RankingFactor("graph_centrality", 0.0, 0.3, "Error calculating structure score")
    
    def _calculate_recency_factor(self, result: Any, context: Dict[str, Any]) -> RankingFactor:
        """Calculate temporal recency factor."""
        try:
            metadata = self._extract_field(result, ['metadata'], {})
            timestamp_str = (
                metadata.get('timestamp') or
                metadata.get('created_at') or
                metadata.get('date')
            )
            
            if not timestamp_str:
                return RankingFactor("recency", 0.5, 0.2, "No timestamp available")
            
            # Parse timestamp
            try:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
                    
                now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
                age_days = (now - timestamp).days
                
                # Exponential decay: newer content gets higher scores
                if age_days <= 0:
                    score = 1.0
                elif age_days <= 7:
                    score = 0.9
                elif age_days <= 30:
                    score = 0.8
                elif age_days <= 90:
                    score = 0.6
                elif age_days <= 365:
                    score = 0.4
                else:
                    score = 0.2
                
                explanation = f"Age: {age_days} days, score: {score:.3f}"
                return RankingFactor("recency", score, 0.2, explanation, age_days)
                
            except Exception as parse_error:
                logger.warning(f"Error parsing timestamp {timestamp_str}: {parse_error}")
                return RankingFactor("recency", 0.5, 0.2, "Invalid timestamp format")
                
        except Exception as e:
            logger.warning(f"Error calculating recency factor: {e}")
            return RankingFactor("recency", 0.5, 0.2, "Error calculating recency")
    
    def _calculate_entity_overlap_factor(self, result: Any, query: str, context: Dict[str, Any]) -> RankingFactor:
        """Calculate entity overlap factor."""
        try:
            metadata = self._extract_field(result, ['metadata'], {})
            
            # Extract entities from result
            result_entities = set()
            
            # Try different entity field names
            entities_data = (
                metadata.get('entities', []) or
                metadata.get('matched_entities', []) or
                metadata.get('related_entities', [])
            )
            
            if isinstance(entities_data, list):
                for entity in entities_data:
                    if isinstance(entity, dict):
                        result_entities.add(entity.get('text', '').lower())
                    else:
                        result_entities.add(str(entity).lower())
            
            # Extract entities from query (simple keyword extraction for now)
            query_words = set(query.lower().split())
            
            # Calculate overlap
            overlap = len(result_entities.intersection(query_words))
            total_entities = max(1, len(result_entities))
            
            score = min(1.0, overlap / max(1, min(len(query_words), total_entities)))
            
            explanation = f"Entity overlap: {overlap}/{total_entities}"
            return RankingFactor("entity_overlap", score, 0.1, explanation, overlap)
            
        except Exception as e:
            logger.warning(f"Error calculating entity overlap: {e}")
            return RankingFactor("entity_overlap", 0.0, 0.1, "Error calculating entity overlap")
    
    def _calculate_content_quality_factor(self, result: Any, context: Dict[str, Any]) -> RankingFactor:
        """Calculate content quality factor."""
        try:
            content = self._extract_field(result, ['content', 'text', 'document'], '')
            
            # Quality metrics
            length = len(content)
            
            # Length factor (prefer moderate length)
            if length < 50:
                length_score = 0.3
            elif length < 200:
                length_score = 1.0
            elif length < 500:
                length_score = 0.8
            elif length < 1000:
                length_score = 0.6
            else:
                length_score = 0.4
            
            # Simple readability (sentence structure)
            sentences = content.count('.') + content.count('!') + content.count('?')
            words = len(content.split())
            readability_score = 1.0 if words == 0 else min(1.0, sentences / max(1, words / 15))
            
            # Combine quality factors
            quality_score = (length_score * 0.7 + readability_score * 0.3)
            
            explanation = f"Content quality: length={length}, readability={readability_score:.2f}"
            return RankingFactor("content_quality", quality_score, 0.0, explanation, {
                "length": length,
                "readability": readability_score
            })
            
        except Exception as e:
            logger.warning(f"Error calculating content quality: {e}")
            return RankingFactor("content_quality", 0.5, 0.0, "Error calculating quality")
    
    def _apply_strategy_modifications(self, 
                                    factors: List[RankingFactor], 
                                    strategy: RankingStrategy,
                                    result: Any,
                                    context: Dict[str, Any]) -> List[RankingFactor]:
        """Apply strategy-specific modifications to ranking factors."""
        try:
            if strategy == RankingStrategy.SEMANTIC_ONLY:
                # Boost semantic, reduce others
                for factor in factors:
                    if factor.name == "semantic_similarity":
                        factor.score = min(1.0, factor.score * 1.2)
                    else:
                        factor.score = factor.score * 0.5
                        
            elif strategy == RankingStrategy.STRUCTURAL_ONLY:
                # Boost structural, reduce others
                for factor in factors:
                    if factor.name == "graph_centrality":
                        factor.score = min(1.0, factor.score * 1.2)
                    else:
                        factor.score = factor.score * 0.5
                        
            elif strategy == RankingStrategy.TEMPORAL_BOOST:
                # Heavily boost recency
                for factor in factors:
                    if factor.name == "recency":
                        factor.score = min(1.0, factor.score * 1.5)
                        
            elif strategy == RankingStrategy.ENTITY_FOCUSED:
                # Boost entity overlap and structural scores
                for factor in factors:
                    if factor.name in ["entity_overlap", "graph_centrality"]:
                        factor.score = min(1.0, factor.score * 1.3)
            
            return factors
            
        except Exception as e:
            logger.warning(f"Error applying strategy modifications: {e}")
            return factors
    
    def _calculate_unified_score(self, factors: List[RankingFactor], weights: RankingWeights) -> float:
        """Calculate unified score from individual factors and weights."""
        try:
            total_score = 0.0
            weight_mapping = {
                "semantic_similarity": weights.semantic_similarity,
                "graph_centrality": weights.graph_centrality,
                "recency": weights.recency,
                "entity_overlap": weights.entity_overlap,
                "content_quality": weights.content_quality
            }
            
            for factor in factors:
                weight = weight_mapping.get(factor.name, 0.0)
                factor.weight = weight  # Update factor weight for explanation
                total_score += factor.score * weight
            
            return min(1.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating unified score: {e}")
            return 0.0
    
    def _extract_field(self, obj: Any, field_names: List[str], default: Any = None, transform=None) -> Any:
        """Extract field from object trying multiple field names."""
        try:
            for field_name in field_names:
                if hasattr(obj, field_name):
                    value = getattr(obj, field_name)
                elif isinstance(obj, dict) and field_name in obj:
                    value = obj[field_name]
                else:
                    continue
                
                if value is not None:
                    return transform(value) if transform else value
            
            return default
            
        except Exception:
            return default
    
    def _calculate_text_similarity(self, query: str, content: str) -> float:
        """Simple text similarity calculation as fallback."""
        try:
            if not query or not content:
                return 0.0
            
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            
            if not query_words:
                return 0.0
            
            intersection = query_words.intersection(content_words)
            similarity = len(intersection) / len(query_words)
            
            return min(1.0, similarity)
            
        except Exception:
            return 0.0
    
    def get_ranking_explanation(self, ranked_result: RankedResult) -> str:
        """Generate human-readable ranking explanation."""
        try:
            explanations = []
            
            explanations.append(f"Overall Score: {ranked_result.unified_score:.3f}")
            explanations.append("Breakdown:")
            
            for factor in ranked_result.ranking_factors:
                contribution = factor.score * factor.weight
                explanations.append(
                    f"  • {factor.name}: {factor.score:.3f} × {factor.weight:.1f} = {contribution:.3f} - {factor.explanation}"
                )
            
            return "\n".join(explanations)
            
        except Exception as e:
            return f"Error generating explanation: {e}"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ranker health status."""
        return {
            "service": "ContextRanker",
            "status": "healthy",
            "default_strategy": self.default_strategy.value,
            "default_weights": {
                "semantic_similarity": self.default_weights.semantic_similarity,
                "graph_centrality": self.default_weights.graph_centrality,
                "recency": self.default_weights.recency,
                "entity_overlap": self.default_weights.entity_overlap,
                "content_quality": self.default_weights.content_quality
            },
            "available_strategies": [strategy.value for strategy in RankingStrategy]
        }