# batch_genai_processor.py
from genai_explainer import GenAIExplainer
from google.cloud import bigquery
import json
import os
import time

def process_high_risk_merchants():
    """Generate explanations for high-risk merchants"""
    
    project_id = os.environ['GOOGLE_CLOUD_PROJECT']
    genai = GenAIExplainer(project_id)
    client = bigquery.Client()
    
    # Find high-risk merchants without explanations
    query = f"""
    SELECT DISTINCT merchant_id, risk_score
    FROM `{project_id}.brand_risk_engine.onboarding`
    WHERE risk_score >= 0.4
    AND merchant_id NOT IN (
        SELECT merchant_id 
        FROM `{project_id}.brand_risk_engine.genai_explanations`
        WHERE explanation_type = 'onboarding'
    )
    """
    
    results = client.query(query).to_dataframe()
    
    for _, row in results.iterrows():
        merchant_id = row['merchant_id']
        
        print(f"Generating explanation for {merchant_id}...")
        explanation = genai.generate_onboarding_explanation(merchant_id)
        
        # Store explanation
        insert_query = f"""
        INSERT INTO `{project_id}.brand_risk_engine.genai_explanations`
        (merchant_id, explanation_type, generated_text, risk_score, trigger_event, model_version)
        VALUES (
            '{merchant_id}',
            'onboarding',
            '''{explanation}''',
            {row['risk_score']},
            'high_risk_detection',
            'text-bison@002'
        )
        """
        
        client.query(insert_query)
        print(f"Stored explanation for {merchant_id}")

def process_reputation_alerts():
    """Generate PR briefs for reputation alerts"""
    
    project_id = os.environ['GOOGLE_CLOUD_PROJECT']
    genai = GenAIExplainer(project_id)
    client = bigquery.Client()
    
    # Find merchants with high reputation risk
    query = f"""
    SELECT merchant_id, max_reputation_risk, volume_spike_count
    FROM `{project_id}.brand_risk_engine.reputation_risk_summary`
    WHERE max_reputation_risk >= 0.7 OR volume_spike_count > 0
    """
    
    results = client.query(query).to_dataframe()
    
    for _, row in results.iterrows():
        merchant_id = row['merchant_id']
        
        print(f"Generating PR brief for {merchant_id}...")
        brief = genai.generate_pr_brief(merchant_id)
        
        # Store PR alert
        alert_id = f"pr_{merchant_id}_{int(time.time())}"
        insert_query = f"""
        INSERT INTO `{project_id}.brand_risk_engine.pr_alerts`
        (alert_id, merchant_id, alert_type, trigger_event, pr_brief, severity)
        VALUES (
            '{alert_id}',
            '{merchant_id}',
            'reputation_crisis',
            'volume_spike_detected',
            '''{brief}''',
            'HIGH'
        )
        """
        
        client.query(insert_query)
        print(f"Created PR alert for {merchant_id}")

if __name__ == '__main__':
    process_high_risk_merchants()
    process_reputation_alerts()