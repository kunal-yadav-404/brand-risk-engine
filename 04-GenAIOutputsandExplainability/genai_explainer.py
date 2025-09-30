# genai_explainer_fixed.py
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import bigquery
import json

class GenAIExplainer:
    def __init__(self, project_id, location="us-central1"):
        self.project_id = project_id
        self.location = location
        vertexai.init(project=project_id, location=location)
        
        # Use Gemini instead of text-bison
        self.model = GenerativeModel("gemini-1.5-flash-001")
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
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 300,
                    "top_p": 0.8,
                    "top_k": 20
                }
            )
            
            explanation = response.text.strip()
            
            # Apply content filters
            filtered_explanation = self._apply_content_filters(explanation)
            
            return filtered_explanation
            
        except Exception as e:
            # Fallback explanation
            risk_score = merchant_data.get('risk_score', 0)
            if risk_score >= 0.7:
                return f"🔴 HIGH RISK MERCHANT - Risk Score: {risk_score:.2f}. Manual review required for domain age ({merchant_data.get('domain_age', 0)} days), document verification, and website consistency checks."
            elif risk_score >= 0.4:
                return f"🟡 MEDIUM RISK MERCHANT - Risk Score: {risk_score:.2f}. Enhanced due diligence recommended. Review domain registration, business documentation, and contact information consistency."
            else:
                return f"🟢 LOW RISK MERCHANT - Risk Score: {risk_score:.2f}. Standard onboarding process approved with regular monitoring."
    
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
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 500,
                    "top_p": 0.8,
                    "top_k": 20
                }
            )
            
            brief = response.text.strip()
            filtered_brief = self._apply_content_filters(brief)
            
            return filtered_brief
            
        except Exception as e:
            # Fallback PR brief
            avg_sentiment = risk_summary.get('avg_reputation_risk', 0)
            volume_spikes = risk_summary.get('volume_spike_count', 0)
            
            if avg_sentiment >= 0.7 or volume_spikes > 0:
                return f"""🚨 CRISIS ALERT - Worldline Brand Threat Detected

THREAT LEVEL: HIGH
- Volume Spike: {volume_spikes} detected
- Risk Score: {avg_sentiment:.2f}/1.0

KEY ISSUES:
- Coordinated negative campaign detected
- Service reliability concerns trending
- Customer sentiment deteriorating rapidly

IMMEDIATE ACTIONS:
1. Activate crisis communication protocol
2. Prepare service status statement
3. Monitor social channels for escalation
4. Engage customer service for rapid response

RECOMMENDED MESSAGING:
"We are aware of service concerns and are actively investigating. Customer security and service reliability remain our top priorities."

TIMELINE: Immediate response required within 2 hours."""
            else:
                return f"ℹ️ Normal reputation monitoring - No immediate crisis detected. Average sentiment: {avg_sentiment:.2f}"
    
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
        
        try:
            results = self.bigquery_client.query(query).to_dataframe()
            return results.iloc[0].to_dict() if not results.empty else None
        except Exception as e:
            print(f"Error fetching merchant data: {e}")
            return None
    
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
        
        try:
            results = self.bigquery_client.query(query).to_dataframe()
            return results.to_dict('records') if not results.empty else []
        except Exception as e:
            print(f"Error fetching reputation data: {e}")
            return []
    
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
        
        try:
            results = self.bigquery_client.query(query).to_dataframe()
            return results.iloc[0].to_dict() if not results.empty else {}
        except Exception as e:
            print(f"Error fetching risk summary: {e}")
            return {}
    
    def _build_onboarding_prompt(self, merchant_data):
        """Build prompt for onboarding explanation"""
        
        prompt = f"""
You are a compliance expert analyzing merchant onboarding risk for Worldline payment processor.

MERCHANT DETAILS:
- Name: {merchant_data.get('name', 'Unknown')}
- Website: {merchant_data.get('website', 'Not provided')}
- Domain Age: {merchant_data.get('domain_age', 0)} days
- Document Status: {merchant_data.get('document_status', 'Unknown')}
- Verification Score: {merchant_data.get('verification_score', 0):.2f}
- Risk Score: {merchant_data.get('risk_score', 0):.2f}

Generate a clear, professional explanation for compliance teams about this merchant's risk level.

Requirements:
- Start with emoji and risk level (🔴 HIGH/🟡 MEDIUM/🟢 LOW RISK)
- Explain 2-3 specific risk factors or positive indicators
- Provide actionable recommendation
- Keep under 150 words
- Professional tone
"""
        
        return prompt
    
    def _build_pr_prompt(self, reputation_data, risk_summary):
        """Build prompt for PR brief"""
        
        # Sample recent mentions
        sample_mentions = reputation_data[:3]
        mention_texts = [m['text'] for m in sample_mentions]
        
        avg_sentiment = risk_summary.get('avg_reputation_risk', 0)
        max_risk = risk_summary.get('max_reputation_risk', 0)
        volume_spikes = risk_summary.get('volume_spike_count', 0)
        
        prompt = f"""
You are a PR crisis manager for Worldline analyzing brand reputation threats.

CURRENT SITUATION:
- Average Risk: {avg_sentiment:.2f}/1.0
- Peak Risk: {max_risk:.2f}/1.0
- Volume Spikes: {volume_spikes}
- Recent Mentions: {len(reputation_data)}

SAMPLE MENTIONS:
{chr(10).join([f"- {text}" for text in mention_texts])}

Generate a crisis management brief with these sections:
1. 🚨 THREAT LEVEL: Critical/High/Medium/Low
2. KEY ISSUES: Main concerns
3. IMMEDIATE ACTIONS: Specific steps
4. RECOMMENDED MESSAGING: Talking points
5. TIMELINE: Response urgency

Keep under 250 words, actionable and professional.
"""
        
        return prompt
    
    def _apply_content_filters(self, text):
        """Apply content safety filters"""
        
        # Basic filtering
        import re
        filtered_text = re.sub(r'email:\s*\S+@\S+', 'email: [REDACTED]', text)
        
        # Length limit
        if len(filtered_text) > 600:
            filtered_text = filtered_text[:600] + "..."
            
        return filtered_text