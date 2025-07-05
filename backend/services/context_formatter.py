"""Context formatting service for LLM consumption."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import tiktoken
from collections import defaultdict

from services.context_aggregator import AggregatedContext, ContextResult

logger = logging.getLogger(__name__)


class ContextFormatter:
    """Service for formatting aggregated context for LLM consumption."""
    
    def __init__(self, 
                 model_name: str = "gpt-3.5-turbo",
                 max_tokens: int = 2000,
                 include_metadata: bool = True):
        """Initialize context formatter.
        
        Args:
            model_name: Model name for token counting
            max_tokens: Maximum token limit for formatted context
            include_metadata: Whether to include metadata in formatting
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.include_metadata = include_metadata
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base encoding
            self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"Model {model_name} not found, using cl100k_base encoding")
    
    def format_for_llm(self, 
                       context: AggregatedContext,
                       max_tokens: Optional[int] = None,
                       priority_order: List[str] = None) -> str:
        """Format aggregated context for LLM consumption.
        
        Args:
            context: Aggregated context from search
            max_tokens: Maximum tokens (overrides default)
            priority_order: Priority order for result types ['vector', 'graph', 'hybrid']
            
        Returns:
            Formatted context string within token limit
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
            
        if priority_order is None:
            priority_order = ['hybrid', 'vector', 'graph', 'related']
        
        try:
            # Group results by source type
            results_by_type = self._group_results_by_type(context.results)
            
            # Start building formatted context
            formatted_sections = []
            current_tokens = 0
            
            # Add header with query metadata
            header = self._format_header(context)
            header_tokens = self._count_tokens(header)
            
            if header_tokens < max_tokens:
                formatted_sections.append(header)
                current_tokens += header_tokens
            
            # Process results by priority
            for source_type in priority_order:
                if source_type not in results_by_type:
                    continue
                    
                results = results_by_type[source_type]
                section = self._format_result_section(source_type, results, 
                                                    max_tokens - current_tokens)
                
                section_tokens = self._count_tokens(section)
                if current_tokens + section_tokens <= max_tokens:
                    formatted_sections.append(section)
                    current_tokens += section_tokens
                else:
                    # Try to fit partial section
                    truncated_section = self._truncate_section(section, 
                                                              max_tokens - current_tokens)
                    if truncated_section:
                        formatted_sections.append(truncated_section)
                    break
            
            # Add summary footer if space remains
            if current_tokens < max_tokens - 100:  # Leave space for footer
                footer = self._format_footer(context)
                footer_tokens = self._count_tokens(footer)
                if current_tokens + footer_tokens <= max_tokens:
                    formatted_sections.append(footer)
            
            return "\n\n".join(formatted_sections)
            
        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            return self._format_fallback(context)
    
    def _group_results_by_type(self, results: List[ContextResult]) -> Dict[str, List[ContextResult]]:
        """Group results by source type."""
        grouped = defaultdict(list)
        for result in results:
            grouped[result.source_type].append(result)
        return dict(grouped)
    
    def _format_header(self, context: AggregatedContext) -> str:
        """Format header section with query metadata."""
        header_parts = ["## Retrieved Context"]
        
        if self.include_metadata:
            query_info = context.query_metadata
            header_parts.extend([
                f"**Query**: {query_info.get('query', 'N/A')}",
                f"**Strategy**: {context.aggregation_strategy}",
                f"**Total Results**: {context.total_results}",
                f"**Processing Time**: {context.processing_time_ms:.1f}ms"
            ])
        
        return "\n".join(header_parts)
    
    def _format_result_section(self, source_type: str, 
                              results: List[ContextResult], 
                              max_tokens: int) -> str:
        """Format a section of results from a specific source type."""
        section_parts = [f"### {self._get_section_title(source_type)}"]
        current_tokens = self._count_tokens(section_parts[0])
        
        for i, result in enumerate(results, 1):
            # Format individual result
            formatted_result = self._format_single_result(result, i)
            result_tokens = self._count_tokens(formatted_result)
            
            # Check if adding this result would exceed limit
            if current_tokens + result_tokens > max_tokens:
                # Add truncation notice
                remaining = len(results) - i + 1
                if remaining > 0:
                    section_parts.append(f"\n*[{remaining} additional results truncated]*")
                break
            
            section_parts.append(formatted_result)
            current_tokens += result_tokens
        
        return "\n\n".join(section_parts)
    
    def _format_single_result(self, result: ContextResult, index: int) -> str:
        """Format a single context result."""
        parts = [f"**[{index}]** (Relevance: {result.relevance_score:.2f})"]
        
        # Add content
        content = result.content.strip()
        if len(content) > 500:
            content = content[:497] + "..."
        parts.append(content)
        
        # Add metadata if enabled
        if self.include_metadata:
            metadata_parts = []
            
            # Add timestamp if available
            if 'timestamp' in result.metadata:
                try:
                    ts = datetime.fromisoformat(result.metadata['timestamp'].replace('Z', '+00:00'))
                    metadata_parts.append(f"Date: {ts.strftime('%Y-%m-%d %H:%M')}")
                except:
                    pass
            
            # Add audio reference
            if 'audio_id' in result.metadata:
                metadata_parts.append(f"Audio: {result.metadata['audio_id'][:8]}...")
            
            # Add entities for graph results
            if result.graph_relationships:
                entities = []
                for rel in result.graph_relationships:
                    if 'matched_entity' in rel:
                        entities.append(rel['matched_entity'])
                if entities:
                    metadata_parts.append(f"Entities: {', '.join(entities[:3])}")
            
            # Add tags if present
            if 'tags' in result.metadata and result.metadata['tags']:
                tags = result.metadata['tags']
                if isinstance(tags, list) and tags:
                    metadata_parts.append(f"Tags: {', '.join(tags[:3])}")
            
            if metadata_parts:
                parts.append(f"*{' | '.join(metadata_parts)}*")
        
        return "\n".join(parts)
    
    def _format_footer(self, context: AggregatedContext) -> str:
        """Format footer with summary statistics."""
        footer_parts = ["### Context Summary"]
        
        # Count by source type
        type_counts = defaultdict(int)
        for result in context.results:
            type_counts[result.source_type] += 1
        
        if type_counts:
            sources = ", ".join([f"{count} {source}" for source, count in type_counts.items()])
            footer_parts.append(f"**Sources**: {sources}")
        
        # Add score distribution
        if context.results:
            avg_score = sum(r.relevance_score for r in context.results) / len(context.results)
            max_score = max(r.relevance_score for r in context.results)
            footer_parts.append(f"**Relevance**: Avg {avg_score:.2f}, Max {max_score:.2f}")
        
        return "\n".join(footer_parts)
    
    def _get_section_title(self, source_type: str) -> str:
        """Get formatted section title for source type."""
        titles = {
            'vector': '📚 Semantic Matches',
            'graph': '🔗 Entity Relationships', 
            'hybrid': '🎯 Combined Results',
            'ensemble': '🔄 Ensemble Results',
            'related': '↪️ Related Context'
        }
        return titles.get(source_type, f"Results from {source_type}")
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback to approximate count
            return len(text) // 4
    
    def _truncate_section(self, section: str, max_tokens: int) -> Optional[str]:
        """Truncate section to fit within token limit."""
        if max_tokens <= 0:
            return None
        
        try:
            tokens = self.encoding.encode(section)
            if len(tokens) <= max_tokens:
                return section
            
            # Truncate tokens and decode
            truncated_tokens = tokens[:max_tokens - 10]  # Leave space for ellipsis
            truncated_text = self.encoding.decode(truncated_tokens)
            
            # Find last complete sentence or newline
            for delimiter in ['\n', '. ', '! ', '? ']:
                last_pos = truncated_text.rfind(delimiter)
                if last_pos > len(truncated_text) // 2:  # At least keep half
                    truncated_text = truncated_text[:last_pos + len(delimiter)]
                    break
            
            return truncated_text + "\n*[Truncated]*"
            
        except Exception as e:
            logger.warning(f"Error truncating section: {e}")
            # Fallback to character-based truncation
            chars_estimate = max_tokens * 4
            return section[:chars_estimate] + "\n*[Truncated]*"
    
    def _format_fallback(self, context: AggregatedContext) -> str:
        """Fallback formatting when main formatting fails."""
        parts = ["## Retrieved Context\n"]
        
        for i, result in enumerate(context.results[:10], 1):  # Limit to 10 results
            parts.append(f"{i}. {result.content[:200]}...")
            if i >= 5 and len(context.results) > 10:
                parts.append(f"\n*[{len(context.results) - 5} additional results]*")
                break
        
        return "\n\n".join(parts)
    
    def format_for_specific_model(self, context: AggregatedContext, 
                                 model_type: str) -> str:
        """Format context optimized for specific model types.
        
        Args:
            context: Aggregated context
            model_type: Type of model ('chat', 'completion', 'instruction')
            
        Returns:
            Model-specific formatted context
        """
        if model_type == 'chat':
            return self._format_for_chat_model(context)
        elif model_type == 'completion':
            return self._format_for_completion_model(context)
        elif model_type == 'instruction':
            return self._format_for_instruction_model(context)
        else:
            return self.format_for_llm(context)
    
    def _format_for_chat_model(self, context: AggregatedContext) -> str:
        """Format specifically for chat models."""
        # Chat models benefit from conversational structure
        parts = ["Based on the retrieved context, here's what I found:\n"]
        
        # Group by relevance tiers
        high_relevance = [r for r in context.results if r.relevance_score >= 0.8]
        medium_relevance = [r for r in context.results if 0.5 <= r.relevance_score < 0.8]
        
        if high_relevance:
            parts.append("**Most Relevant Information:**")
            for result in high_relevance[:3]:
                parts.append(f"- {result.content[:150]}...")
        
        if medium_relevance:
            parts.append("\n**Additional Context:**")
            for result in medium_relevance[:2]:
                parts.append(f"- {result.content[:100]}...")
        
        return "\n".join(parts)
    
    def _format_for_completion_model(self, context: AggregatedContext) -> str:
        """Format specifically for completion models."""
        # Completion models work better with continuous text
        parts = []
        
        for result in context.results[:5]:  # Top 5 results
            parts.append(result.content)
        
        return " ".join(parts)
    
    def _format_for_instruction_model(self, context: AggregatedContext) -> str:
        """Format specifically for instruction-following models."""
        # Instruction models benefit from structured format
        instruction = "Use the following context to answer the query:\n\n"
        
        context_parts = []
        for i, result in enumerate(context.results[:5], 1):
            context_parts.append(f"Context {i}:\n{result.content}\n")
        
        return instruction + "\n".join(context_parts)