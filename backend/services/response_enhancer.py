"""Response enhancement service for enriching LLM responses."""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
import json

from services.context_aggregator import AggregatedContext, ContextResult

logger = logging.getLogger(__name__)


@dataclass
class EnhancedResponse:
    """Enhanced response with rich formatting and metadata."""
    original_response: str
    enhanced_response: str
    citations: List[Dict[str, Any]]
    related_topics: List[str]
    follow_up_suggestions: List[str]
    confidence_score: Optional[float] = None
    processing_metadata: Dict[str, Any] = None


class ResponseEnhancer:
    """Service for enhancing LLM responses with rich formatting and citations."""
    
    def __init__(self,
                 include_citations: bool = True,
                 include_suggestions: bool = True,
                 markdown_format: bool = True):
        """Initialize response enhancer.
        
        Args:
            include_citations: Whether to add source citations
            include_suggestions: Whether to add follow-up suggestions
            markdown_format: Whether to use markdown formatting
        """
        self.include_citations = include_citations
        self.include_suggestions = include_suggestions
        self.markdown_format = markdown_format
        
        # Citation patterns to detect referenced content
        self.citation_patterns = [
            r'according to (?:the )?(?:audio|transcript|conversation)',
            r'(?:you|they|he|she) (?:mentioned|said|discussed)',
            r'in (?:the|your) (?:meeting|discussion|conversation)',
            r'(?:the|this) (?:document|file|recording) (?:shows|indicates)',
            r'based on (?:the|your) (?:previous|past|earlier)'
        ]
        
        # Topic extraction patterns
        self.topic_patterns = {
            'project': r'\b(?:project|initiative|effort)\s+(?:[A-Z]\w+)',
            'person': r'\b(?:with|from|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'date': r'\b(?:on|at|during)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            'technology': r'\b(?:using|with|via)\s+([A-Z]\w+(?:\s+\w+)?)\b'
        }
    
    def enhance_response(self,
                        response: str,
                        context: AggregatedContext,
                        query: Optional[str] = None,
                        confidence_score: Optional[float] = None) -> EnhancedResponse:
        """Enhance LLM response with rich formatting and metadata.
        
        Args:
            response: Original LLM response
            context: Aggregated context used for generation
            query: Original user query
            confidence_score: Optional confidence score
            
        Returns:
            Enhanced response with citations and formatting
        """
        try:
            logger.info("Enhancing response with citations and formatting")
            
            # Initialize processing metadata
            processing_metadata = {
                'enhancement_start': datetime.now().isoformat(),
                'context_sources': len(context.results),
                'original_length': len(response)
            }
            
            # Step 1: Identify content that needs citations
            citation_points = self._identify_citation_points(response)
            
            # Step 2: Match citations to context sources
            citations = self._create_citations(citation_points, context)
            
            # Step 3: Add inline citations to response
            enhanced_response = self._add_inline_citations(response, citations)
            
            # Step 4: Extract related topics
            related_topics = self._extract_related_topics(response, context)
            
            # Step 5: Generate follow-up suggestions
            follow_up_suggestions = self._generate_follow_up_suggestions(
                response, context, query
            )
            
            # Step 6: Format the final response
            if self.markdown_format:
                enhanced_response = self._format_markdown_response(
                    enhanced_response, citations, related_topics, follow_up_suggestions
                )
            
            # Update metadata
            processing_metadata['enhancement_end'] = datetime.now().isoformat()
            processing_metadata['citations_added'] = len(citations)
            processing_metadata['enhanced_length'] = len(enhanced_response)
            
            return EnhancedResponse(
                original_response=response,
                enhanced_response=enhanced_response,
                citations=citations,
                related_topics=related_topics,
                follow_up_suggestions=follow_up_suggestions,
                confidence_score=confidence_score,
                processing_metadata=processing_metadata
            )
            
        except Exception as e:
            logger.error(f"Error enhancing response: {e}")
            # Return minimal enhancement on error
            return EnhancedResponse(
                original_response=response,
                enhanced_response=response,
                citations=[],
                related_topics=[],
                follow_up_suggestions=[]
            )
    
    def _identify_citation_points(self, response: str) -> List[Dict[str, Any]]:
        """Identify points in response that need citations.
        
        Args:
            response: LLM response text
            
        Returns:
            List of citation points with positions and patterns
        """
        citation_points = []
        
        # Look for citation patterns
        for pattern in self.citation_patterns:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                citation_points.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(0),
                    'pattern': pattern,
                    'type': self._get_citation_type(pattern)
                })
        
        # Look for specific claims or facts
        fact_patterns = [
            r'(\d+(?:\.\d+)?%)',  # Percentages
            r'(\$\d+(?:,\d{3})*(?:\.\d{2})?)',  # Money amounts
            r'(\d+(?:,\d{3})*)\s+(?:people|users|customers|employees)',  # Counts
            r'(?:in|on|at)\s+(\d{4})',  # Years
        ]
        
        for pattern in fact_patterns:
            for match in re.finditer(pattern, response):
                citation_points.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(0),
                    'pattern': pattern,
                    'type': 'fact'
                })
        
        # Sort by position and remove overlaps
        citation_points.sort(key=lambda x: x['start'])
        
        # Remove overlapping citations
        filtered_points = []
        last_end = -1
        for point in citation_points:
            if point['start'] >= last_end:
                filtered_points.append(point)
                last_end = point['end']
        
        return filtered_points
    
    def _create_citations(self, 
                         citation_points: List[Dict[str, Any]], 
                         context: AggregatedContext) -> List[Dict[str, Any]]:
        """Create citations from context sources.
        
        Args:
            citation_points: Identified citation points
            context: Aggregated context
            
        Returns:
            List of citations with source information
        """
        citations = []
        used_sources = set()
        
        for i, point in enumerate(citation_points):
            # Find best matching source
            best_source = self._find_best_source(point, context.results, used_sources)
            
            if best_source:
                citation = {
                    'id': i + 1,
                    'text': point['text'],
                    'type': point['type'],
                    'source': {
                        'content': best_source.content[:200] + '...' if len(best_source.content) > 200 else best_source.content,
                        'relevance_score': best_source.relevance_score,
                        'source_type': best_source.source_type
                    }
                }
                
                # Add metadata based on source type
                if best_source.metadata:
                    if 'audio_id' in best_source.metadata:
                        citation['source']['audio_id'] = best_source.metadata['audio_id']
                    if 'timestamp' in best_source.metadata:
                        citation['source']['timestamp'] = best_source.metadata['timestamp']
                    if 'chunk_index' in best_source.metadata:
                        citation['source']['position'] = f"Position {best_source.metadata['chunk_index']}"
                
                citations.append(citation)
                used_sources.add(best_source.id)
        
        return citations
    
    def _add_inline_citations(self, response: str, citations: List[Dict[str, Any]]) -> str:
        """Add inline citations to response text.
        
        Args:
            response: Original response
            citations: List of citations
            
        Returns:
            Response with inline citations
        """
        if not citations or not self.include_citations:
            return response
        
        # Create citation map by text
        citation_map = {cite['text']: f"[{cite['id']}]" for cite in citations}
        
        # Sort by length descending to handle longer matches first
        sorted_texts = sorted(citation_map.keys(), key=len, reverse=True)
        
        enhanced = response
        for text in sorted_texts:
            citation_ref = citation_map[text]
            # Add citation after the text
            pattern = re.escape(text)
            enhanced = re.sub(
                f'({pattern})(?![\\d\\]])',  # Negative lookahead to avoid double citations
                f'\\1 {citation_ref}',
                enhanced,
                count=1  # Only replace first occurrence
            )
        
        return enhanced
    
    def _extract_related_topics(self, 
                              response: str, 
                              context: AggregatedContext) -> List[str]:
        """Extract related topics from response and context.
        
        Args:
            response: LLM response
            context: Aggregated context
            
        Returns:
            List of related topics
        """
        topics = set()
        
        # Extract from response
        for topic_type, pattern in self.topic_patterns.items():
            for match in re.finditer(pattern, response):
                topic = match.group(1) if match.groups() else match.group(0)
                topics.add(topic.strip())
        
        # Extract from context metadata
        for result in context.results[:5]:  # Top 5 results
            if result.metadata:
                # Add tags
                if 'tags' in result.metadata and isinstance(result.metadata['tags'], list):
                    topics.update(result.metadata['tags'])
                
                # Add entities from graph relationships
                if result.graph_relationships:
                    for rel in result.graph_relationships:
                        if 'related_entities' in rel:
                            topics.update(rel['related_entities'][:3])
        
        # Filter and clean topics
        cleaned_topics = []
        for topic in topics:
            if isinstance(topic, str) and len(topic) > 2 and len(topic) < 50:
                cleaned_topics.append(topic)
        
        return sorted(list(set(cleaned_topics)))[:10]  # Top 10 topics
    
    def _generate_follow_up_suggestions(self,
                                      response: str,
                                      context: AggregatedContext,
                                      query: Optional[str] = None) -> List[str]:
        """Generate follow-up question suggestions.
        
        Args:
            response: LLM response
            context: Aggregated context
            query: Original query
            
        Returns:
            List of follow-up suggestions
        """
        if not self.include_suggestions:
            return []
        
        suggestions = []
        
        # Analyze response for incomplete information
        incomplete_patterns = [
            (r'(?:for more|additional|further) (?:details|information)', 
             "Can you provide more details about this?"),
            (r'(?:several|multiple|various) (?:options|approaches|methods)',
             "What are the different options available?"),
            (r'(?:depends on|varies by|based on)',
             "What factors does this depend on?"),
            (r'(?:typically|usually|generally)',
             "Are there any exceptions to this?")
        ]
        
        for pattern, suggestion in incomplete_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                suggestions.append(suggestion)
        
        # Analyze context for unexplored areas
        if context.results:
            # Check for temporal progression
            has_past = any('last' in str(r.metadata) or 'previous' in str(r.metadata) 
                          for r in context.results)
            if has_past:
                suggestions.append("How has this changed over time?")
            
            # Check for multiple entities
            entities = set()
            for result in context.results[:5]:
                if result.metadata and 'matched_entity' in result.metadata:
                    entities.add(result.metadata['matched_entity'])
            
            if len(entities) > 2:
                suggestions.append("Can you compare these different aspects?")
        
        # Query-based suggestions
        if query:
            query_lower = query.lower()
            if 'how' in query_lower and 'why' not in response.lower():
                suggestions.append("Why is this approach recommended?")
            elif 'what' in query_lower and 'when' not in response.lower():
                suggestions.append("When should this be done?")
            elif 'who' in query_lower and 'where' not in response.lower():
                suggestions.append("Where does this apply?")
        
        # Limit suggestions
        return suggestions[:3]
    
    def _format_markdown_response(self,
                                response: str,
                                citations: List[Dict[str, Any]],
                                related_topics: List[str],
                                suggestions: List[str]) -> str:
        """Format response with markdown.
        
        Args:
            response: Response with inline citations
            citations: List of citations
            related_topics: List of related topics
            suggestions: Follow-up suggestions
            
        Returns:
            Markdown formatted response
        """
        parts = [response]
        
        # Add citations section
        if citations and self.include_citations:
            parts.append("\n\n---\n### 📚 Sources")
            for cite in citations:
                source = cite['source']
                cite_text = f"\n**[{cite['id']}]** "
                
                # Add timestamp if available
                if 'timestamp' in source:
                    try:
                        ts = datetime.fromisoformat(source['timestamp'].replace('Z', '+00:00'))
                        cite_text += f"*{ts.strftime('%Y-%m-%d')}* - "
                    except:
                        pass
                
                # Add content preview
                cite_text += f"{source['content']}"
                
                # Add metadata
                metadata_parts = []
                if 'audio_id' in source:
                    metadata_parts.append(f"Audio: {source['audio_id'][:8]}...")
                if 'position' in source:
                    metadata_parts.append(source['position'])
                if 'relevance_score' in source:
                    metadata_parts.append(f"Relevance: {source['relevance_score']:.2f}")
                
                if metadata_parts:
                    cite_text += f"\n   *{' | '.join(metadata_parts)}*"
                
                parts.append(cite_text)
        
        # Add related topics section
        if related_topics:
            parts.append("\n\n### 🔗 Related Topics")
            topics_text = " • ".join([f"`{topic}`" for topic in related_topics])
            parts.append(topics_text)
        
        # Add suggestions section
        if suggestions and self.include_suggestions:
            parts.append("\n\n### 💡 Follow-up Questions")
            for i, suggestion in enumerate(suggestions, 1):
                parts.append(f"{i}. {suggestion}")
        
        return "\n".join(parts)
    
    def _get_citation_type(self, pattern: str) -> str:
        """Determine citation type from pattern.
        
        Args:
            pattern: Regex pattern used
            
        Returns:
            Citation type
        """
        if 'according to' in pattern:
            return 'reference'
        elif 'mentioned' in pattern or 'said' in pattern:
            return 'quote'
        elif 'document' in pattern or 'file' in pattern:
            return 'document'
        elif 'based on' in pattern:
            return 'inference'
        else:
            return 'general'
    
    def _find_best_source(self,
                         citation_point: Dict[str, Any],
                         results: List[ContextResult],
                         used_sources: Set[str]) -> Optional[ContextResult]:
        """Find best matching source for citation.
        
        Args:
            citation_point: Citation point information
            results: Available context results
            used_sources: Already used source IDs
            
        Returns:
            Best matching context result or None
        """
        # Filter out already used sources
        available_results = [r for r in results if r.id not in used_sources]
        
        if not available_results:
            return None
        
        # Score results based on citation type
        scored_results = []
        for result in available_results:
            score = result.relevance_score
            
            # Boost score based on citation type match
            if citation_point['type'] == 'quote' and result.source_type == 'vector':
                score *= 1.2
            elif citation_point['type'] == 'reference' and result.source_type == 'graph':
                score *= 1.1
            elif citation_point['type'] == 'fact' and 'entity_count' in result.metadata:
                score *= 1.15
            
            scored_results.append((score, result))
        
        # Sort by score and return best
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[0][1] if scored_results else None
    
    def format_for_voice(self, enhanced_response: EnhancedResponse) -> str:
        """Format response for voice output (TTS).
        
        Args:
            enhanced_response: Enhanced response object
            
        Returns:
            Voice-friendly formatted response
        """
        # Start with original response (no citations for voice)
        voice_response = enhanced_response.original_response
        
        # Remove markdown formatting
        voice_response = re.sub(r'\*\*(.*?)\*\*', r'\1', voice_response)  # Bold
        voice_response = re.sub(r'\*(.*?)\*', r'\1', voice_response)  # Italic
        voice_response = re.sub(r'`(.*?)`', r'\1', voice_response)  # Code
        voice_response = re.sub(r'#{1,6}\s+', '', voice_response)  # Headers
        
        # Replace bullet points with pauses
        voice_response = re.sub(r'^\s*[-•]\s+', 'Next, ', voice_response, flags=re.MULTILINE)
        
        # Add pauses for better speech flow
        voice_response = re.sub(r'([.!?])\s+', r'\1 <break time="0.5s"/> ', voice_response)
        voice_response = re.sub(r',\s+', r', <break time="0.3s"/> ', voice_response)
        
        # Add suggestions as a separate section
        if enhanced_response.follow_up_suggestions:
            voice_response += ' <break time="1s"/> If you'd like to know more, you could ask: '
            for i, suggestion in enumerate(enhanced_response.follow_up_suggestions):
                if i > 0:
                    voice_response += ' Or, '
                voice_response += suggestion
        
        return voice_response
    
    def format_for_display(self, enhanced_response: EnhancedResponse,
                          format_type: str = 'markdown') -> str:
        """Format response for different display types.
        
        Args:
            enhanced_response: Enhanced response object
            format_type: Display format ('markdown', 'html', 'plain')
            
        Returns:
            Formatted response
        """
        if format_type == 'markdown':
            return enhanced_response.enhanced_response
        elif format_type == 'plain':
            # Strip markdown formatting
            plain = enhanced_response.enhanced_response
            plain = re.sub(r'\*\*(.*?)\*\*', r'\1', plain)
            plain = re.sub(r'\*(.*?)\*', r'\1', plain)
            plain = re.sub(r'`(.*?)`', r'\1', plain)
            plain = re.sub(r'#{1,6}\s+', '', plain)
            plain = re.sub(r'---\n', '\n', plain)
            return plain
        elif format_type == 'html':
            # Convert markdown to HTML (simplified)
            html = enhanced_response.enhanced_response
            html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
            html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
            html = re.sub(r'### (.*?)\n', r'<h3>\1</h3>\n', html)
            html = re.sub(r'\n\n', '</p><p>', html)
            html = f'<p>{html}</p>'
            return html
        else:
            return enhanced_response.enhanced_response