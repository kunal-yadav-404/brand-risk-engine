# simplified_enhanced_pipeline.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import json
import re
from urllib.parse import urlparse

class SimplifiedEnhancedProcessor(beam.DoFn):
    def process(self, element):
        try:
            data = json.loads(element)
            merchant_id = data.get('merchant_id')
            name = data.get('name', '')
            website = data.get('website', '')
            
            # Simple domain analysis
            domain_score, domain_issues = self._analyze_domain(website)
            
            # Simple name-website consistency check
            name_match_score = self._check_name_consistency(name, website)
            
            # Calculate risk score
            risk_score = self._calculate_risk(domain_score, name_match_score, data)
            
            # Generate explanation
            explanation = self._generate_explanation(risk_score, domain_issues, name_match_score)
            
            yield {
                'merchant_id': merchant_id,
                'name': name,
                'website': website,
                'domain_age': self._extract_domain_age_estimate(website),
                'contact_info': json.dumps(data.get('contact_info', {})),
                'document_status': data.get('document_status', 'pending'),
                'verification_score': name_match_score,
                'risk_score': risk_score,
                'explain_text': explanation
            }
            
        except Exception as e:
            print(f"Error processing: {e}")
            # Fallback
            yield {
                'merchant_id': data.get('merchant_id'),
                'name': data.get('name'),
                'website': data.get('website'),
                'domain_age': 0,
                'contact_info': json.dumps(data.get('contact_info', {})),
                'document_status': 'error',
                'verification_score': 0.0,
                'risk_score': 0.5,
                'explain_text': f'Processing error: {str(e)}'
            }
    
    def _analyze_domain(self, website):
        """Simple domain analysis"""
        issues = []
        score = 0.5  # neutral
        
        if not website:
            return 0.0, ["No website provided"]
            
        # Basic URL validation
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
            
        try:
            parsed = urlparse(website)
            domain = parsed.netloc
            
            # Check for suspicious TLDs
            suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.click']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                issues.append("Suspicious TLD")
                score -= 0.3
                
            # Check for HTTPS
            if parsed.scheme == 'https':
                score += 0.2
            else:
                issues.append("No HTTPS")
                
            # Simple domain length check
            if len(domain) < 5:
                issues.append("Very short domain")
                score -= 0.2
                
            score = max(0.0, min(1.0, score))
            
        except:
            issues.append("Invalid URL format")
            score = 0.0
            
        return score, issues
    
    def _check_name_consistency(self, name, website):
        """Check if business name appears in domain"""
        if not name or not website:
            return 0.0
            
        # Extract domain
        try:
            parsed = urlparse(website if website.startswith('http') else 'https://' + website)
            domain = parsed.netloc.lower()
            
            # Simple name matching
            name_words = re.findall(r'\w+', name.lower())
            domain_clean = re.sub(r'[^a-z]', '', domain)
            
            matches = 0
            for word in name_words:
                if len(word) > 3 and word in domain_clean:
                    matches += 1
                    
            if name_words:
                return matches / len(name_words)
            return 0.0
            
        except:
            return 0.0
    
    def _calculate_risk(self, domain_score, name_match_score, data):
        """Calculate overall risk score"""
        risk_factors = []
        
        # Domain risk (inverted - low domain score = high risk)
        risk_factors.append(1.0 - domain_score)
        
        # Name consistency risk
        risk_factors.append(1.0 - name_match_score)
        
        # Missing email risk
        email = data.get('contact_info', {}).get('email')
        if not email:
            risk_factors.append(0.3)
        else:
            risk_factors.append(0.0)
            
        # Calculate average risk
        avg_risk = sum(risk_factors) / len(risk_factors)
        return min(1.0, max(0.0, avg_risk))
    
    def _generate_explanation(self, risk_score, domain_issues, name_match_score):
        """Generate human-readable explanation"""
        explanations = []
        
        # Risk level
        if risk_score >= 0.7:
            explanations.append("🔴 HIGH RISK")
        elif risk_score >= 0.4:
            explanations.append("🟡 MEDIUM RISK")
        else:
            explanations.append("🟢 LOW RISK")
            
        # Domain issues
        if domain_issues:
            explanations.append(f"Domain issues: {', '.join(domain_issues[:2])}")
            
        # Name matching
        if name_match_score < 0.3:
            explanations.append("Business name not found in domain")
        elif name_match_score > 0.7:
            explanations.append("Good name-domain match")
            
        # Risk score
        explanations.append(f"Risk score: {risk_score:.2f}")
        
        return " | ".join(explanations)
    
    def _extract_domain_age_estimate(self, website):
        """Simple domain age estimate (placeholder)"""
        # In real implementation, would use whois
        if website and 'test' in website.lower():
            return 30  # Assume test domains are new
        return 365  # Default assumption

def run_simplified_enhanced_pipeline():
    pipeline_options = PipelineOptions([
        '--project=' + PROJECT_ID,
        '--region=' + REGION,
        '--runner=DataflowRunner',
        '--temp_location=gs://brand-risk-temp/temp',
        '--staging_location=gs://brand-risk-temp/staging',
        '--setup_file=./setup.py'
    ])
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(
             subscription=f'projects/{PROJECT_ID}/subscriptions/onboarding-dataflow-sub')
         | 'Enhanced Processing' >> beam.ParDo(SimplifiedEnhancedProcessor())
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             table=f'{PROJECT_ID}:brand_risk_engine.onboarding',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED))

if __name__ == '__main__':
    import os
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    REGION = 'us-central1'
    run_simplified_enhanced_pipeline()