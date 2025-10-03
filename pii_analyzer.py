"""
PII Analyzer using Microsoft Presidio
Handles detection and analysis of personally identifiable information
"""

import logging
from typing import List, Dict, Any, Optional, Union
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PIIAnalyzer:
    """Main PII Analysis class using Presidio"""
    
    def __init__(self, language: str = 'en', entities: List[str] = None):
        """
        Initialize the PII Analyzer
        
        Args:
            language: Language code for analysis
            entities: List of entity types to detect
        """
        self.language = language or Config.DEFAULT_LANGUAGE
        self.entities = entities or Config.DEFAULT_PII_ENTITIES
        
        # Initialize Presidio engines
        try:
            self._initialize_analyzer()
            self._initialize_anonymizer()
            logger.info("PII Analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PII Analyzer: {str(e)}")
            raise
    
    def _initialize_analyzer(self):
        """Initialize the Presidio Analyzer Engine"""
        try:
            # Create NLP configuration
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": self.language, "model_name": "en_core_web_sm"}],
            }
            
            # Create NLP engine
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            
            # Create analyzer engine
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            
        except Exception as e:
            logger.error(f"Failed to initialize analyzer engine: {str(e)}")
            # Fallback to default configuration
            self.analyzer = AnalyzerEngine()
    
    def _initialize_anonymizer(self):
        """Initialize the Presidio Anonymizer Engine"""
        try:
            self.anonymizer = AnonymizerEngine()
        except Exception as e:
            logger.error(f"Failed to initialize anonymizer engine: {str(e)}")
            raise
    
    def analyze_text(self, 
                    text: str, 
                    entities: List[str] = None,
                    language: str = None,
                    score_threshold: float = None) -> List[Dict[str, Any]]:
        """
        Analyze text for PII entities
        
        Args:
            text: Text to analyze
            entities: List of entity types to detect
            language: Language for analysis
            score_threshold: Minimum confidence score
            
        Returns:
            List of detected PII entities with metadata
        """
        if not text or not isinstance(text, str):
            return []
        
        try:
            # Set parameters
            analysis_entities = entities or self.entities
            analysis_language = language or self.language
            threshold = score_threshold or Config.CONFIDENCE_THRESHOLD
            
            # Perform analysis
            results = self.analyzer.analyze(
                text=text,
                entities=analysis_entities,
                language=analysis_language,
                score_threshold=threshold
            )
            
            # Convert results to dictionary format
            pii_results = []
            for result in results:
                pii_data = {
                    'entity_type': result.entity_type,
                    'start': result.start,
                    'end': result.end,
                    'score': round(result.score, 3),
                    'recognition_metadata': result.recognition_metadata,
                    'text': text[result.start:result.end]
                }
                pii_results.append(pii_data)
            
            # Sort by start position
            pii_results.sort(key=lambda x: x['start'])
            
            logger.info(f"Found {len(pii_results)} PII entities in text")
            return pii_results
            
        except Exception as e:
            logger.error(f"Error analyzing text: {str(e)}")
            return []
    
    def anonymize_text(self, 
                      text: str,
                      analyzer_results: List[Dict[str, Any]] = None,
                      anonymization_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Anonymize text based on detected PII
        
        Args:
            text: Original text
            analyzer_results: Pre-analyzed PII results
            anonymization_config: Custom anonymization configuration
            
        Returns:
            Dictionary with anonymized text and metadata
        """
        if not text:
            return {'text': '', 'items': []}
        
        try:
            # Get PII analysis if not provided
            if analyzer_results is None:
                analyzer_results = self.analyze_text(text)
            
            # Convert results to Presidio format
            presidio_results = []
            for result in analyzer_results:
                presidio_results.append(
                    type('RecognizerResult', (), {
                        'entity_type': result['entity_type'],
                        'start': result['start'],
                        'end': result['end'],
                        'score': result['score']
                    })()
                )
            
            # Set up anonymization configuration
            config = anonymization_config or Config.DEFAULT_ANONYMIZATION_CONFIG
            operators = {}
            
            for entity_type, settings in config.items():
                if settings['type'] == 'replace':
                    operators[entity_type] = OperatorConfig(
                        'replace',
                        {'new_value': settings['new_value']}
                    )
                elif settings['type'] == 'redact':
                    operators[entity_type] = OperatorConfig('redact', {})
                elif settings['type'] == 'mask':
                    operators[entity_type] = OperatorConfig(
                        'mask',
                        {
                            'masking_char': settings.get('masking_char', '*'),
                            'chars_to_mask': settings.get('chars_to_mask', -1),
                            'from_end': settings.get('from_end', False)
                        }
                    )
                elif settings['type'] == 'hash':
                    operators[entity_type] = OperatorConfig('hash', {})
            
            # Perform anonymization
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=presidio_results,
                operators=operators
            )
            
            return {
                'text': anonymized_result.text,
                'items': [
                    {
                        'operator': item.operator,
                        'entity_type': item.entity_type,
                        'start': item.start,
                        'end': item.end,
                        'text': item.text
                    }
                    for item in anonymized_result.items
                ]
            }
            
        except Exception as e:
            logger.error(f"Error anonymizing text: {str(e)}")
            return {'text': text, 'items': []}
    
    def get_supported_entities(self) -> List[str]:
        """Get list of supported entity types"""
        try:
            return self.analyzer.get_supported_entities(language=self.language)
        except Exception as e:
            logger.error(f"Error getting supported entities: {str(e)}")
            return Config.DEFAULT_PII_ENTITIES
    
    def validate_entities(self, entities: List[str]) -> List[str]:
        """Validate and filter entity types"""
        if not entities:
            return self.entities
        
        supported = self.get_supported_entities()
        valid_entities = [entity for entity in entities if entity in supported]
        
        if not valid_entities:
            logger.warning("No valid entities provided, using defaults")
            return self.entities
        
        return valid_entities
    
    def get_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from PII analysis results"""
        if not results:
            return {
                'total_entities': 0,
                'entity_counts': {},
                'average_confidence': 0,
                'high_confidence_count': 0
            }
        
        entity_counts = {}
        scores = []
        high_confidence = 0
        
        for result in results:
            entity_type = result['entity_type']
            score = result['score']
            
            # Count entities
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
            scores.append(score)
            
            # Count high confidence detections
            if score >= 0.8:
                high_confidence += 1
        
        return {
            'total_entities': len(results),
            'entity_counts': entity_counts,
            'average_confidence': round(sum(scores) / len(scores), 3) if scores else 0,
            'high_confidence_count': high_confidence,
            'confidence_distribution': {
                'high (>= 0.8)': sum(1 for s in scores if s >= 0.8),
                'medium (0.5-0.79)': sum(1 for s in scores if 0.5 <= s < 0.8),
                'low (< 0.5)': sum(1 for s in scores if s < 0.5)
            }
        }


# Global analyzer instance
_analyzer_instance = None

def get_analyzer(language: str = 'en', entities: List[str] = None) -> PIIAnalyzer:
    """Get or create global analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = PIIAnalyzer(language=language, entities=entities)
    return _analyzer_instance