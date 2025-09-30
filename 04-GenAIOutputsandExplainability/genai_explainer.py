# genai_explainer.py
import vertexai
from vertexai.language_models import TextGenerationModel
from google.cloud import bigquery
import json

class GenAIExplainer:
    def __init__(self, project_id, location="us-central1"):
        self.project_id = project_id
        self.location = location
        vertexai.init(project=project_id, location=location)
        self.model = TextGenerationModel.from_pretrained("text-bison@002")
        self.bigquery_client = bigquery.Client()
        
    def generate_onboarding_explanation(self, merchant_id):
        """Generate human-readable onboarding risk explanation"""
        
        # Get merchant data
        merchant_data = self._get_merchant_data(merchant_id)
        if not merchant_data:
            return "Merchant data not found"
            
        # Build prompt
        prompt = self._build_onboarding_prompt(merchant_data)
        
        # Generate explanation
        try:
            response = self.model.predict(
                prompt=prompt,
                temperature=0.2,  # Low temperature for consistency
                max_output_tokens=300,
                top_p=0.8,
                top_k=20
            )
            
            explanation = response.text.strip()
            
            # Apply content filters
            filtered_explanation = self._apply_content_filters(explanation)
            
            return filtered_explanation
            
        except Exception as e:
            return f"Error generating explanation: {str(e)}"
    
    def generate_pr_brief(self, merchant_id, time_window_hours=24):
        """Generate PR crisis brief"""
        
        # Get reputation data
        reputation_data = self._get_reputation_data(merchant_id, time_window_hours)
        risk_summary = self._get_risk_summary(merchant_id)
        
        if not reputation_data:
            return "No recent reputation data found"
            
        # Build PR prompt
        prompt = self._build_pr_prompt(reputation_data, risk_summary)
        
        try:
            response = self.model.predict(
                prompt=prompt,
                temperature=0.3,
                max_output_tokens=500,
                top_p=0.8,
                top_k=20
            )
            
            brief = response.text.strip()
            filtered_brief = self._apply_content_filters(brief)
            
            return filtered_brief
            
        except Exception as e:
            return f"Error generating PR brief: {str(e)}"
    
    def _get_merchant_data(self, merchant_id):
        """Fetch merchant onboarding data"""
        query = f"""
        SELECT 
            merchant_id,
            name,
            website,
            domain_age,
            contact_info,
            document_status,
            verification_score,
            risk_score,
            explain_text
        FROM `{self.project_id}.brand_risk_engine.onboarding`
        WHERE merchant_id = '{merchant_id}'
        ORDER BY updated_at DESC
        LIMIT 1
        """
        
        results = self.bigquery_client.query(query).to_dataframe()
        return results.iloc[0].to_dict() if not results.empty else None
    
    def _get_reputation_data(self, merchant_id, hours=24):
        """Fetch recent reputation mentions"""
        query = f"""
        SELECT 
            source,
            sentiment,
            text,
            timestamp,
            COUNT(*) OVER() as total_mentions,
            AVG(sentiment) OVER() as avg_sentiment
        FROM `{self.project_id}.brand_risk_engine.reputation`
        WHERE merchant_id = '{merchant_id}'
        AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        ORDER BY timestamp DESC
        LIMIT 10
        """
        
        results = self.bigquery_client.query(query).to_dataframe()
        return results.to_dict('records') if not results.empty else []
    
    def _get_risk_summary(self, merchant_id):
        """Get risk summary"""
        query = f"""
        SELECT 
            avg_reputation_risk,
            max_reputation_risk,
            alert_count,
            volume_spike_count
        FROM `{self.project_id}.brand_risk_engine.reputation_risk_summary`
        WHERE merchant_id = '{merchant_id}'
        """
        
        results = self.bigquery_client.query(query).to_dataframe()
        return results.iloc[0].to_dict() if not results.empty else {}
    
    def _build_onboarding_prompt(self, merchant_data):
        """Build prompt for onboarding explanation"""
        
        prompt = f"""
You are a compliance expert analyzing merchant onboarding risk for a payment processor.

MERCHANT DETAILS:
- Name: {merchant_data.get('name', 'Unknown')}
- Website: {merchant_data.get('website', 'Not provided')}
- Domain Age: {merchant_data.get('domain_age', 0)} days
- Document Status: {merchant_data.get('document_status', 'Unknown')}
- Verification Score: {merchant_data.get('verification_score', 0):.2f}
- Risk Score: {merchant_data.get('risk_score', 0):.2f}

TASK: Generate a clear, professional explanation for compliance teams about this merchant's risk level.

REQUIREMENTS:
- Start with risk level (LOW/MEDIUM/HIGH RISK)
- Explain 2-3 specific risk factors or positive indicators
- Provide actionable recommendation
- Keep under 200 words
- Use professional, clear language
- Focus on facts, not speculation

EXPLANATION:
"""
        
        return prompt
    
    def _build_pr_prompt(self, reputation_data, risk_summary):
        """Build prompt for PR brief"""
        
        # Sample recent mentions
        sample_mentions = reputation_data[:5]
        mention_texts = [m['text'] for m in sample_mentions]
        
        avg_sentiment = risk_summary.get('avg_reputation_risk', 0)
        max_risk = risk_summary.get('max_reputation_risk', 0)
        volume_spikes = risk_summary.get('volume_spike_count', 0)
        
        prompt = f"""
You are a PR crisis management expert analyzing brand reputation threats for Worldline.

CURRENT SITUATION:
- Average Risk Level: {avg_sentiment:.2f} (0=low, 1=critical)
- Peak Risk Score: {max_risk:.2f}
- Volume Spikes Detected: {volume_spikes}
- Total Recent Mentions: {len(reputation_data)}

SAMPLE RECENT MENTIONS:
{chr(10).join([f"- {text}" for text in mention_texts[:3]])}

TASK: Generate a crisis management brief for the PR team.

REQUIRED SECTIONS:
1. THREAT LEVEL: Critical/High/Medium/Low
2. KEY ISSUES: 2-3 main concerns from mentions
3. RECOMMENDED ACTIONS: Specific PR responses
4. MESSAGING: Suggested talking points
5. TIMELINE: Urgency level

Keep professional, actionable, and under 300 words.

PR BRIEF:
"""
        
        return prompt
    
    def _apply_content_filters(self, text):
        """Apply content safety filters"""
        
        # Remove potential sensitive information
        filtered_text = text
        
        # Remove any quoted personal information
        import re
        filtered_text = re.sub(r'email:\s*\S+@\S+', 'email: [REDACTED]', filtered_text)
        filtered_text = re.sub(r'phone:\s*[\d\-\(\)\s]+', 'phone: [REDACTED]', filtered_text)
        
        # Ensure appropriate tone
        inflammatory_words = ['terrible', 'awful', 'worst', 'horrible']
        for word in inflammatory_words:
            filtered_text = filtered_text.replace(word, 'concerning')
        
        # Length limit
        if len(filtered_text) > 600:
            filtered_text = filtered_text[:600] + "..."
            
        return filtered_text