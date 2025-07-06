"""Named Entity Recognition service using spaCy."""
import logging
from typing import List, Dict, Any, Optional
import spacy
from spacy.lang.en import English
from spacy.lang.fr import French
from spacy.lang.es import Spanish
from spacy.lang.de import German

logger = logging.getLogger(__name__)


class NERService:
    """Named Entity Recognition service with multi-language support."""
    
    def __init__(self):
        """Initialize NER service with language models."""
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """Load spaCy models for supported languages."""
        # Model configurations: (language_code, model_name, fallback_model)
        model_configs = [
            ('en', 'en_core_web_sm', 'en_core_web_sm'),
            ('fr', 'fr_core_news_sm', 'fr_core_news_sm'),
            ('es', 'es_core_news_sm', 'es_core_news_sm'),
            ('de', 'de_core_news_sm', 'de_core_news_sm'),
        ]
        
        for lang_code, model_name, fallback in model_configs:
            try:
                # Try to load the full model
                self.models[lang_code] = spacy.load(model_name)
                logger.info(f"Loaded spaCy model for {lang_code}: {model_name}")
            except OSError as e:
                try:
                    # Try fallback model
                    logger.warning(f"Could not load spaCy model for {lang_code}, using blank model", e)
                    self.models[lang_code] = spacy.load(fallback)
                    logger.info(f"Loaded fallback spaCy model for {lang_code}: {fallback}")
                except OSError as e:
                    # Use blank model as last resort
                    logger.warning(f"Could not load spaCy model for {lang_code}, using blank model")
                    self.models[lang_code] = self._create_blank_model(lang_code)
        
        # Default to English if no model is available
        if not self.models:
            logger.warning("No spaCy models available, creating blank English model")
            self.models['en'] = self._create_blank_model('en')
    
    def _create_blank_model(self, lang_code: str):
        """Create a blank spaCy model for basic tokenization."""
        if lang_code == 'en':
            return English()
        elif lang_code == 'fr':
            return French()
        elif lang_code == 'es':
            return Spanish()
        elif lang_code == 'de':
            return German()
        else:
            return English()  # Default to English
    
    def extract_entities(
        self, 
        text: str, 
        language: str = 'en',
        include_positions: bool = True
    ) -> List[Dict[str, Any]]:
        """Extract named entities from text.
        
        Args:
            text: Text to process
            language: Language code (en, fr, es, de)
            include_positions: Whether to include character positions
            
        Returns:
            List of entity dictionaries with text, label, start, end
        """
        if not text or not text.strip():
            return []
        
        # Get model for language, fallback to English
        model = self.models.get(language, self.models.get('en'))
        if not model:
            logger.error("No spaCy model available")
            return []
        
        try:
            # Process text
            doc = model(text)
            
            entities = []
            for ent in doc.ents:
                entity = {
                    'text': ent.text,
                    'label': ent.label_,
                    'label_description': spacy.explain(ent.label_) or ent.label_,
                    'confidence': getattr(ent, 'confidence', 1.0)
                }
                
                if include_positions:
                    entity.update({
                        'start': ent.start_char,
                        'end': ent.end_char
                    })
                
                entities.append(entity)
            
            # Remove duplicates and sort by position
            entities = self._deduplicate_entities(entities)
            
            if include_positions:
                entities.sort(key=lambda x: x['start'])
            
            logger.debug(f"Extracted {len(entities)} entities from text ({language})")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities based on text and position.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Deduplicated list of entities
        """
        seen = set()
        deduplicated = []
        
        for entity in entities:
            # Create key based on text and position (if available)
            if 'start' in entity and 'end' in entity:
                key = (entity['text'].lower(), entity['start'], entity['end'])
            else:
                key = entity['text'].lower()
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
        
        return deduplicated
    
    def extract_entities_with_context(
        self, 
        text: str, 
        language: str = 'en',
        context_window: int = 50
    ) -> List[Dict[str, Any]]:
        """Extract entities with surrounding context.
        
        Args:
            text: Text to process
            language: Language code
            context_window: Number of characters around entity for context
            
        Returns:
            List of entities with context information
        """
        entities = self.extract_entities(text, language, include_positions=True)
        
        for entity in entities:
            if 'start' in entity and 'end' in entity:
                start_pos = entity['start']
                end_pos = entity['end']
                
                # Extract context
                context_start = max(0, start_pos - context_window)
                context_end = min(len(text), end_pos + context_window)
                
                context = text[context_start:context_end]
                
                # Calculate relative position within context
                relative_start = start_pos - context_start
                relative_end = end_pos - context_start
                
                entity.update({
                    'context': context,
                    'context_start': context_start,
                    'context_end': context_end,
                    'relative_start': relative_start,
                    'relative_end': relative_end
                })
        
        return entities
    
    def get_entity_frequencies(
        self, 
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """Get frequency counts for entities by type.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            Dictionary with entity type frequencies
        """
        frequencies = {}
        
        for entity in entities:
            label = entity.get('label', 'UNKNOWN')
            text = entity.get('text', '').strip()
            
            if label not in frequencies:
                frequencies[label] = {}
            
            if text:
                frequencies[label][text] = frequencies[label].get(text, 0) + 1
        
        return frequencies
    
    def filter_entities_by_type(
        self, 
        entities: List[Dict[str, Any]], 
        entity_types: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter entities by type.
        
        Args:
            entities: List of entity dictionaries
            entity_types: List of entity types to keep (e.g., ['PERSON', 'ORG'])
            
        Returns:
            Filtered list of entities
        """
        return [
            entity for entity in entities 
            if entity.get('label') in entity_types
        ]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes.
        
        Returns:
            List of supported language codes
        """
        return list(self.models.keys())
    
    def get_model_info(self, language: str = None) -> Dict[str, Any]:
        """Get information about loaded models.
        
        Args:
            language: Specific language to get info for, or None for all
            
        Returns:
            Dictionary with model information
        """
        if language:
            model = self.models.get(language)
            if model:
                return {
                    'language': language,
                    'model_name': model.meta.get('name', 'unknown'),
                    'version': model.meta.get('version', 'unknown'),
                    'has_ner': model.has_pipe('ner')
                }
            return {}
        
        return {
            lang: {
                'model_name': model.meta.get('name', 'unknown'),
                'version': model.meta.get('version', 'unknown'),
                'has_ner': model.has_pipe('ner')
            }
            for lang, model in self.models.items()
        }