# reputation_pipeline_enhanced.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
from datetime import datetime

class ReputationProcessor(beam.DoFn):
    def setup(self):
        from nlp_processor import NLPProcessor
        self.nlp = NLPProcessor(PROJECT_ID)
    
    def process(self, element):
        try:
            data = json.loads(element)
            
            # NLP Analysis
            text = data.get('text', '')
            nlp_result = self.nlp.analyze_sentiment(text)
            
            # Detect Worldline mentions
            worldline_mentions = self.nlp.detect_worldline_mentions(text)
            
            # Classify mention type
            mention_type = self.nlp.classify_mention_type(text, nlp_result['entities'])
            
            # Calculate enhanced sentiment
            enhanced_sentiment = self._calculate_enhanced_sentiment(
                nlp_result['sentiment_score'],
                nlp_result['sentiment_magnitude'],
                mention_type
            )
            
            yield {
                'merchant_id': data.get('merchant_id', 'UNKNOWN'),
                'source': data.get('source', 'unknown'),
                'mention_id': data.get('mention_id'),
                'text': text,
                'sentiment': enhanced_sentiment,
                'sentiment_raw': nlp_result['sentiment_score'],
                'magnitude': nlp_result['sentiment_magnitude'],
                'mention_type': mention_type,
                'entities': json.dumps(nlp_result['entities']),
                'worldline_mentions': json.dumps(worldline_mentions),
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'language': nlp_result['language'],
                'raw_data': json.dumps(data)
            }
            
        except Exception as e:
            print(f"Error processing reputation data: {e}")
    
    def _calculate_enhanced_sentiment(self, score, magnitude, mention_type):
        """Enhanced sentiment calculation"""
        
        # Adjust sentiment based on mention type
        type_modifiers = {
            'service_issue': -0.3,
            'security_concern': -0.5,
            'positive_feedback': 0.2,
            'pricing_concern': -0.2,
            'general_mention': 0.0
        }
        
        modifier = type_modifiers.get(mention_type, 0.0)
        
        # Weight by magnitude (higher magnitude = more confident sentiment)
        weighted_score = score * magnitude
        
        # Apply type modifier
        final_score = weighted_score + modifier
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, final_score))

def run_reputation_pipeline():
    pipeline_options = PipelineOptions([
        '--project=' + PROJECT_ID,
        '--region=' + REGION,
        '--runner=DataflowRunner',
        '--temp_location=gs://brand-risk-temp/temp',
        '--staging_location=gs://brand-risk-temp/staging'
    ])
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(
             subscription=f'projects/{PROJECT_ID}/subscriptions/reputation-dataflow-sub')
         | 'NLP Processing' >> beam.ParDo(ReputationProcessor())
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=f'{PROJECT_ID}:brand_risk_engine.reputation',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))