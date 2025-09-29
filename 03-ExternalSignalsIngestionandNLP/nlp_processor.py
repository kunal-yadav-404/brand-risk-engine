# nlp_processor.py
from google.cloud import aiplatform
from google.cloud import language_v1
import json

class NLPProcessor:
    def __init__(self, project_id, location="us-central1"):
        self.project_id = project_id
        self.location = location
        self.language_client = language_v1.LanguageServiceClient()
        
    def analyze_sentiment(self, text):
        """Analyze sentiment using Cloud Natural Language API"""
        try:
            document = language_v1.Document(
                content=text,
                type_=language_v1.Document.Type.PLAIN_TEXT
            )
            
            # Sentiment analysis
            sentiment_response = self.language_client.analyze_sentiment(
                request={"document": document}
            )
            
            # Entity analysis
            entity_response = self.language_client.analyze_entities(
                request={"document": document}
            )
            
            return {
                'sentiment_score': sentiment_response.document_sentiment.score,
                'sentiment_magnitude': sentiment_response.document_sentiment.magnitude,
                'entities': [
                    {
                        'name': entity.name,
                        'type': entity.type_.name,
                        'salience': entity.salience
                    }
                    for entity in entity_response.entities
                ],
                'language': sentiment_response.language
            }
            
        except Exception as e:
            print(f"NLP analysis error: {e}")
            return {
                'sentiment_score': 0.0,
                'sentiment_magnitude': 0.0,
                'entities': [],
                'language': 'unknown'
            }
    
    def detect_worldline_mentions(self, text):
        """Detect Worldline-related mentions"""
        worldline_keywords = [
            'worldline', 'world line', 'payment processor',
            'merchant services', 'payment gateway'
        ]
        
        text_lower = text.lower()
        mentions = []
        
        for keyword in worldline_keywords:
            if keyword in text_lower:
                mentions.append(keyword)
                
        return mentions
    
    def classify_mention_type(self, text, entities):
        """Classify type of mention"""
        text_lower = text.lower()
        
        # Service issues
        if any(word in text_lower for word in ['down', 'failed', 'error', 'problem']):
            return 'service_issue'
        
        # Fraud/Security
        if any(word in text_lower for word in ['fraud', 'scam', 'suspicious', 'hack']):
            return 'security_concern'
        
        # Positive feedback
        if any(word in text_lower for word in ['great', 'excellent', 'love', 'smooth']):
            return 'positive_feedback'
        
        # Pricing concerns
        if any(word in text_lower for word in ['expensive', 'fees', 'cost', 'price']):
            return 'pricing_concern'
        
        return 'general_mention'