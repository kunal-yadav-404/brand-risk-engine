# enhanced_onboarding_pipeline.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
from document_processor import DocumentProcessor
from domain_checker import DomainChecker

class EnhancedOnboardingProcessor(beam.DoFn):
    def __init__(self, project_id, processor_id):
        self.project_id = project_id
        self.processor_id = processor_id
        
    def setup(self):
        self.doc_processor = DocumentProcessor(self.project_id, self.processor_id)
        self.domain_checker = DomainChecker()
        
    def process(self, element):
        try:
            data = json.loads(element)
            merchant_id = data.get('merchant_id')
            
            # Document processing
            doc_result = {}
            if data.get('document_gcs_uri'):
                doc_result = self.doc_processor.process_document(
                    data['document_gcs_uri'], 
                    merchant_id
                )
            
            # Domain verification
            domain_result = self.domain_checker.check_domain(
                data.get('website'),
                data.get('name')
            )
            
            # Enhanced feature calculation
            features = self._calculate_features(data, doc_result, domain_result)
            
            # Generate explanation
            explanation = self._generate_explanation(features, doc_result, domain_result)
            
            yield {
                'merchant_id': merchant_id,
                'name': data.get('name'),
                'website': data.get('website'),
                'domain_age': domain_result.get('checks', {}).get('domain_age', 0),
                'contact_info': json.dumps(data.get('contact_info', {})),
                'document_status': 'verified' if doc_result.get('validation_score', 0) > 0.7 else 'pending',
                'verification_score': doc_result.get('validation_score', 0.0),
                'risk_score': features['risk_score'],
                'explain_text': explanation,
                'domain_check_results': json.dumps(domain_result),
                'document_analysis': json.dumps(doc_result)
            }
            
        except Exception as e:
            print(f"Error processing merchant {data.get('merchant_id')}: {e}")
            
    def _calculate_features(self, merchant_data, doc_result, domain_result):
        """Calculate risk features"""
        
        # Domain features
        domain_score = domain_result.get('score', 0.0)
        domain_age = domain_result.get('checks', {}).get('domain_age', 0)
        
        # Document features  
        doc_score = doc_result.get('validation_score', 0.0)
        
        # Basic features
        has_website = bool(merchant_data.get('website'))
        email_provided = bool(merchant_data.get('contact_info', {}).get('email'))
        
        # Calculate composite risk score
        risk_factors = []
        
        # Domain age risk
        if domain_age < 30:
            risk_factors.append(0.3)
        elif domain_age < 90:
            risk_factors.append(0.1)
        else:
            risk_factors.append(0.0)
            
        # Domain reputation risk
        risk_factors.append(1.0 - domain_score)
        
        # Document verification risk
        if doc_score < 0.5:
            risk_factors.append(0.4)
        else:
            risk_factors.append(0.0)
            
        # Missing info risk
        if not has_website:
            risk_factors.append(0.2)
        if not email_provided:
            risk_factors.append(0.1)
            
        # Final risk score (average of risk factors)
        risk_score = sum(risk_factors) / len(risk_factors) if risk_factors else 0.0
        risk_score = min(risk_score, 1.0)
        
        return {
            'risk_score': risk_score,
            'domain_score': domain_score,
            'doc_score': doc_score,
            'risk_factors': risk_factors
        }
    
    def _generate_explanation(self, features, doc_result, domain_result):
        """Generate human-readable explanation"""
        explanations = []
        
        risk_score = features['risk_score']
        
        # Risk level
        if risk_score >= 0.7:
            explanations.append("HIGH RISK MERCHANT")
        elif risk_score >= 0.4:
            explanations.append("MEDIUM RISK MERCHANT")
        else:
            explanations.append("LOW RISK MERCHANT")
            
        # Domain issues
        domain_issues = domain_result.get('issues', [])
        if domain_issues:
            explanations.append(f"Domain concerns: {', '.join(domain_issues[:2])}")
            
        # Document issues
        doc_anomalies = doc_result.get('anomalies', [])
        if doc_anomalies:
            explanations.append(f"Document issues: {', '.join(doc_anomalies[:2])}")
            
        # Positive factors
        if features['domain_score'] > 0.8:
            explanations.append("Strong domain reputation")
        if features['doc_score'] > 0.8:
            explanations.append("Document verification passed")
            
        return "; ".join(explanations)

def run_enhanced_pipeline():
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
             subscription=f'projects/{PROJECT_ID}/subscriptions/onboarding-dataflow-sub')
         | 'Enhanced Processing' >> beam.ParDo(
             EnhancedOnboardingProcessor(PROJECT_ID, DOC_AI_PROCESSOR_ID))
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=f'{PROJECT_ID}:brand_risk_engine.onboarding',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    run_enhanced_pipeline()