# enhanced_pipeline_with_genai.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
from genai_explainer import GenAIExplainer

class OnboardingWithGenAI(beam.DoFn):
    def setup(self):
        self.genai = GenAIExplainer(PROJECT_ID)
    
    def process(self, element):
        try:
            data = json.loads(element)
            merchant_id = data.get('merchant_id')
            
            # Basic processing (from Day 2)
            processed_data = self._basic_processing(data)
            
            # Generate GenAI explanation
            if processed_data['risk_score'] > 0.3:  # Only for medium+ risk
                genai_explanation = self.genai.generate_onboarding_explanation(merchant_id)
                processed_data['genai_explanation'] = genai_explanation
            else:
                processed_data['genai_explanation'] = "Low risk merchant - standard processing approved"
            
            yield processed_data
            
        except Exception as e:
            print(f"Error in GenAI processing: {e}")
    
    def _basic_processing(self, data):
        # Simplified version of Day 2 processing
        risk_score = 0.5  # Placeholder
        return {
            'merchant_id': data.get('merchant_id'),
            'name': data.get('name'),
            'website': data.get('website'),
            'risk_score': risk_score,
            'explain_text': f"Risk score: {risk_score:.2f}",
        }

class ReputationWithGenAI(beam.DoFn):
    def setup(self):
        self.genai = GenAIExplainer(PROJECT_ID)
    
    def process(self, element):
        try:
            data = json.loads(element)
            merchant_id = data.get('merchant_id')
            
            # Process reputation data
            processed_data = {
                'merchant_id': merchant_id,
                'source': data.get('source'),
                'mention_id': data.get('mention_id'),
                'text': data.get('text'),
                'sentiment': data.get('sentiment', 0.0),
                'timestamp': data.get('timestamp')
            }
            
            yield processed_data
            
            # Check if we need to generate PR brief (high volume or negative sentiment)
            if processed_data['sentiment'] < -0.5:
                pr_brief = self.genai.generate_pr_brief(merchant_id)
                
                # Publish PR alert
                alert_data = {
                    'alert_type': 'PR_BRIEF',
                    'merchant_id': merchant_id,
                    'trigger': 'negative_sentiment',
                    'pr_brief': pr_brief,
                    'timestamp': processed_data['timestamp']
                }
                
                yield beam.pvalue.TaggedOutput('alerts', alert_data)
                
        except Exception as e:
            print(f"Error in reputation GenAI processing: {e}")