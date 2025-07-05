"""Query enhancement service for improving retrieval accuracy."""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from services.ner_service import NERService

logger = logging.getLogger(__name__)


@dataclass
class EnhancedQuery:
    """Enhanced query with additional context and metadata."""
    original_query: str
    enhanced_query: str
    extracted_entities: List[Dict[str, Any]]
    temporal_context: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    query_type: Optional[str] = None
    expansion_terms: List[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = None


class QueryEnhancer:
    """Service for enhancing user queries for better retrieval."""
    
    def __init__(self, ner_service: Optional[NERService] = None):
        """Initialize query enhancer.
        
        Args:
            ner_service: NER service for entity extraction
        """
        self.ner_service = ner_service or NERService()
        
        # Common pronouns and their resolution patterns
        self.pronoun_patterns = {
            'he': 'person_male',
            'she': 'person_female', 
            'they': 'person_plural',
            'it': 'entity',
            'that': 'previous_subject',
            'this': 'current_subject',
            'these': 'current_plural',
            'those': 'previous_plural'
        }
        
        # Common abbreviations
        self.abbreviations = {
            'mtg': 'meeting',
            'msg': 'message',
            'proj': 'project',
            'mgr': 'manager',
            'dept': 'department',
            'req': 'requirement',
            'dev': 'development',
            'prod': 'production',
            'db': 'database',
            'api': 'application programming interface',
            'ui': 'user interface',
            'ux': 'user experience'
        }
        
        # Temporal indicators
        self.temporal_patterns = {
            'today': 0,
            'yesterday': -1,
            'tomorrow': 1,
            'last week': -7,
            'next week': 7,
            'last month': -30,
            'next month': 30,
            'recently': -7,  # Default to last week
            'soon': 7  # Default to next week
        }
        
        # Query intent patterns
        self.intent_patterns = {
            'search': [r'what.*about', r'tell.*about', r'show.*about', r'find'],
            'summary': [r'summar', r'overview', r'brief', r'recap'],
            'clarification': [r'what.*mean', r'explain', r'clarify', r'elaborate'],
            'comparison': [r'compare', r'difference', r'versus', r'vs\.?'],
            'action': [r'how.*to', r'steps.*to', r'way.*to', r'need.*to'],
            'temporal': [r'when', r'what.*time', r'which.*date'],
            'person': [r'who', r'whom', r'whose'],
            'location': [r'where', r'which.*place']
        }
    
    async def enhance_query(self, 
                          query: str,
                          history: List[Dict[str, str]] = None,
                          user_context: Optional[Dict[str, Any]] = None) -> EnhancedQuery:
        """Enhance user query for better retrieval.
        
        Args:
            query: Original user query
            history: Conversation history (list of {"role": "user/assistant", "content": "..."})
            user_context: Optional user context (preferences, location, etc.)
            
        Returns:
            Enhanced query with additional context
        """
        try:
            logger.info(f"Enhancing query: '{query[:100]}...'")
            
            # Initialize enhancement
            enhanced_query = query
            metadata = {}
            
            # Step 1: Resolve pronouns
            enhanced_query, pronoun_resolutions = self._resolve_pronouns(
                enhanced_query, history or []
            )
            if pronoun_resolutions:
                metadata['pronoun_resolutions'] = pronoun_resolutions
            
            # Step 2: Expand abbreviations
            enhanced_query, expanded_terms = self._expand_abbreviations(enhanced_query)
            if expanded_terms:
                metadata['expanded_abbreviations'] = expanded_terms
            
            # Step 3: Add temporal context
            enhanced_query, temporal_context = self._add_temporal_context(
                enhanced_query, user_context
            )
            
            # Step 4: Extract entities
            entities = self._extract_entities(enhanced_query)
            
            # Step 5: Identify intent
            intent = self._identify_intent(enhanced_query)
            
            # Step 6: Determine query type
            query_type = self._determine_query_type(enhanced_query, intent)
            
            # Step 7: Generate expansion terms
            expansion_terms = self._generate_expansion_terms(
                enhanced_query, entities, intent
            )
            
            # Step 8: Extract implicit entities from history
            if history:
                implicit_entities = self._extract_implicit_entities(query, history)
                entities.extend(implicit_entities)
            
            # Calculate confidence based on enhancements made
            confidence = self._calculate_confidence(
                query, enhanced_query, len(entities), bool(temporal_context)
            )
            
            return EnhancedQuery(
                original_query=query,
                enhanced_query=enhanced_query,
                extracted_entities=entities,
                temporal_context=temporal_context,
                intent=intent,
                query_type=query_type,
                expansion_terms=expansion_terms,
                confidence=confidence,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error enhancing query: {e}")
            # Return minimal enhancement on error
            return EnhancedQuery(
                original_query=query,
                enhanced_query=query,
                extracted_entities=[],
                confidence=0.5
            )
    
    def _resolve_pronouns(self, query: str, 
                         history: List[Dict[str, str]]) -> Tuple[str, Dict[str, str]]:
        """Resolve pronouns based on conversation history.
        
        Args:
            query: Query text
            history: Conversation history
            
        Returns:
            Tuple of (resolved query, resolution mapping)
        """
        resolutions = {}
        resolved_query = query
        
        if not history:
            return resolved_query, resolutions
        
        # Find recent entities mentioned in history
        recent_entities = self._extract_recent_entities(history[-5:])  # Last 5 messages
        
        # Common pronoun patterns
        pronoun_regex = r'\b(he|she|they|it|that|this|these|those)\b'
        
        for match in re.finditer(pronoun_regex, query, re.IGNORECASE):
            pronoun = match.group(1).lower()
            
            # Try to resolve based on recent entities
            if pronoun in ['he', 'she', 'they']:
                # Look for person entities
                for entity in recent_entities:
                    if entity.get('type') == 'PERSON':
                        replacement = entity['text']
                        resolved_query = resolved_query.replace(
                            match.group(0), replacement, 1
                        )
                        resolutions[pronoun] = replacement
                        break
            
            elif pronoun in ['it', 'that', 'this']:
                # Look for the most recent non-person entity
                for entity in recent_entities:
                    if entity.get('type') != 'PERSON':
                        replacement = entity['text']
                        resolved_query = resolved_query.replace(
                            match.group(0), replacement, 1
                        )
                        resolutions[pronoun] = replacement
                        break
        
        return resolved_query, resolutions
    
    def _expand_abbreviations(self, query: str) -> Tuple[str, Dict[str, str]]:
        """Expand common abbreviations in query.
        
        Args:
            query: Query text
            
        Returns:
            Tuple of (expanded query, expansions made)
        """
        expanded_query = query
        expansions = {}
        
        # Sort by length descending to handle longer abbreviations first
        sorted_abbrevs = sorted(self.abbreviations.items(), 
                               key=lambda x: len(x[0]), reverse=True)
        
        for abbrev, full_form in sorted_abbrevs:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            if re.search(pattern, expanded_query, re.IGNORECASE):
                expanded_query = re.sub(pattern, full_form, expanded_query, 
                                       flags=re.IGNORECASE)
                expansions[abbrev] = full_form
        
        return expanded_query, expansions
    
    def _add_temporal_context(self, query: str, 
                            user_context: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Add temporal context to query.
        
        Args:
            query: Query text
            user_context: User context with timezone info
            
        Returns:
            Tuple of (query with temporal context, temporal metadata)
        """
        temporal_context = None
        enhanced_query = query
        
        # Get current date (use user timezone if available)
        now = datetime.now()
        
        # Look for temporal indicators
        for indicator, offset_days in self.temporal_patterns.items():
            if indicator in query.lower():
                reference_date = now + timedelta(days=offset_days)
                
                temporal_context = {
                    'indicator': indicator,
                    'reference_date': reference_date.isoformat(),
                    'date_range': {
                        'start': (reference_date - timedelta(days=1)).isoformat(),
                        'end': (reference_date + timedelta(days=1)).isoformat()
                    }
                }
                
                # Add explicit date to query for better search
                date_str = reference_date.strftime('%Y-%m-%d')
                enhanced_query = f"{enhanced_query} (around {date_str})"
                break
        
        # Look for relative date patterns
        relative_patterns = [
            (r'(\d+)\s*days?\s*ago', lambda x: now - timedelta(days=int(x))),
            (r'(\d+)\s*weeks?\s*ago', lambda x: now - timedelta(weeks=int(x))),
            (r'(\d+)\s*months?\s*ago', lambda x: now - timedelta(days=int(x)*30)),
            (r'in\s*(\d+)\s*days?', lambda x: now + timedelta(days=int(x))),
            (r'in\s*(\d+)\s*weeks?', lambda x: now + timedelta(weeks=int(x))),
        ]
        
        for pattern, date_func in relative_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                num = match.group(1)
                reference_date = date_func(num)
                
                temporal_context = {
                    'pattern': match.group(0),
                    'reference_date': reference_date.isoformat(),
                    'date_range': {
                        'start': (reference_date - timedelta(days=1)).isoformat(),
                        'end': (reference_date + timedelta(days=1)).isoformat()
                    }
                }
                break
        
        return enhanced_query, temporal_context
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract entities from query using NER.
        
        Args:
            query: Query text
            
        Returns:
            List of extracted entities
        """
        try:
            # Use NER service to extract entities
            entities = self.ner_service.extract_entities(query)
            
            # Enhance with additional metadata
            enhanced_entities = []
            for entity in entities:
                enhanced_entity = entity.copy()
                enhanced_entity['source'] = 'ner'
                enhanced_entity['confidence'] = entity.get('score', 0.8)
                enhanced_entities.append(enhanced_entity)
            
            return enhanced_entities
            
        except Exception as e:
            logger.warning(f"Failed to extract entities: {e}")
            return []
    
    def _identify_intent(self, query: str) -> Optional[str]:
        """Identify query intent based on patterns.
        
        Args:
            query: Query text
            
        Returns:
            Identified intent or None
        """
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        # Default intent based on question words
        if query_lower.startswith(('what', 'when', 'where', 'who', 'why', 'how')):
            return 'search'
        
        return None
    
    def _determine_query_type(self, query: str, intent: Optional[str]) -> str:
        """Determine the type of query.
        
        Args:
            query: Query text
            intent: Identified intent
            
        Returns:
            Query type
        """
        query_lower = query.lower()
        
        # Check for specific query types
        if '?' in query:
            if intent == 'person':
                return 'person_query'
            elif intent == 'temporal':
                return 'temporal_query'
            elif intent == 'location':
                return 'location_query'
            else:
                return 'question'
        
        # Check for command-like queries
        if query_lower.startswith(('show', 'list', 'find', 'get')):
            return 'command'
        
        # Check for statement vs question
        if intent == 'action':
            return 'how_to'
        elif intent == 'summary':
            return 'summary_request'
        
        return 'general'
    
    def _generate_expansion_terms(self, query: str, 
                                entities: List[Dict[str, Any]], 
                                intent: Optional[str]) -> List[str]:
        """Generate query expansion terms.
        
        Args:
            query: Enhanced query
            entities: Extracted entities
            intent: Query intent
            
        Returns:
            List of expansion terms
        """
        expansion_terms = []
        
        # Add synonyms for key terms
        key_terms = {
            'meeting': ['conference', 'discussion', 'call'],
            'project': ['initiative', 'effort', 'work'],
            'deadline': ['due date', 'timeline', 'schedule'],
            'budget': ['cost', 'expense', 'financial'],
            'team': ['group', 'department', 'colleagues']
        }
        
        query_lower = query.lower()
        for term, synonyms in key_terms.items():
            if term in query_lower:
                expansion_terms.extend(synonyms)
        
        # Add related terms based on intent
        if intent == 'action':
            expansion_terms.extend(['steps', 'process', 'procedure', 'guide'])
        elif intent == 'summary':
            expansion_terms.extend(['overview', 'highlights', 'key points'])
        elif intent == 'comparison':
            expansion_terms.extend(['versus', 'different', 'similar', 'contrast'])
        
        # Add entity-based expansions
        for entity in entities:
            if entity.get('type') == 'PERSON':
                expansion_terms.extend(['said', 'mentioned', 'discussed'])
            elif entity.get('type') == 'ORG':
                expansion_terms.extend(['company', 'organization', 'department'])
        
        # Remove duplicates and return
        return list(set(expansion_terms))
    
    def _extract_recent_entities(self, history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Extract entities from recent conversation history.
        
        Args:
            history: Recent conversation messages
            
        Returns:
            List of entities ordered by recency
        """
        all_entities = []
        
        # Process history in reverse order (most recent first)
        for i, message in enumerate(reversed(history)):
            if message.get('role') in ['user', 'assistant']:
                content = message.get('content', '')
                entities = self.ner_service.extract_entities(content)
                
                # Add recency score
                for entity in entities:
                    entity['recency_score'] = 1.0 / (i + 1)  # More recent = higher score
                    entity['source_role'] = message['role']
                    all_entities.append(entity)
        
        # Sort by recency and return unique entities
        seen = set()
        unique_entities = []
        for entity in sorted(all_entities, key=lambda x: x['recency_score'], reverse=True):
            entity_key = (entity['text'].lower(), entity['type'])
            if entity_key not in seen:
                seen.add(entity_key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_implicit_entities(self, query: str, 
                                 history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Extract entities implicitly referenced in query.
        
        Args:
            query: Current query
            history: Conversation history
            
        Returns:
            List of implicit entities
        """
        implicit_entities = []
        query_lower = query.lower()
        
        # Check for references to previous topics
        if any(word in query_lower for word in ['that', 'this', 'it', 'the same']):
            recent_entities = self._extract_recent_entities(history[-3:])
            
            # Add the most relevant recent entities as implicit
            for entity in recent_entities[:2]:  # Top 2 recent entities
                implicit_entity = entity.copy()
                implicit_entity['implicit'] = True
                implicit_entity['confidence'] = entity.get('confidence', 0.7) * 0.8
                implicit_entities.append(implicit_entity)
        
        return implicit_entities
    
    def _calculate_confidence(self, original: str, enhanced: str, 
                           entity_count: int, has_temporal: bool) -> float:
        """Calculate confidence score for enhancement.
        
        Args:
            original: Original query
            enhanced: Enhanced query
            entity_count: Number of entities extracted
            has_temporal: Whether temporal context was added
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Boost for successful enhancements
        if enhanced != original:
            confidence += 0.2
        
        if entity_count > 0:
            confidence += min(0.2, entity_count * 0.05)
        
        if has_temporal:
            confidence += 0.1
        
        # Penalty for very short queries
        if len(original.split()) < 3:
            confidence *= 0.8
        
        return min(1.0, confidence)