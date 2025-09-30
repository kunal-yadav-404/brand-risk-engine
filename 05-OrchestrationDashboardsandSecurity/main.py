# main.py (Cloud Function)
import functions_framework
from google.cloud import pubsub_v1
from google.cloud import bigquery
from genai_explainer_fixed import GenAIExplainer
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def orchestrate_risk_pipeline(request):
    """Main orchestration function"""
    try:
        # Get request data
        request_json = request.get_json()
        action = request_json.get('action', 'full_pipeline')
        
        if action == 'full_pipeline':
            result = run_full_pipeline()
        elif action == 'reputation_check':
            result = check_reputation_alerts()
        elif action == 'onboarding_review':
            result = review_pending_merchants()
        else:
            result = {'error': 'Unknown action'}
            
        return result
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        return {'error': str(e)}, 500

def run_full_pipeline():
    """Execute complete risk assessment pipeline"""
    logger.info("Starting full pipeline execution")
    
    # Step 1: Process pending onboarding
    onboarding_results = process_onboarding_queue()
    
    # Step 2: Check reputation alerts
    reputation_results = check_reputation_alerts()
    
    # Step 3: Update aggregated risk
    update_aggregated_risk()
    
    # Step 4: Generate alerts
    alert_results = generate_alerts()
    
    return {
        'status': 'completed',
        'onboarding_processed': onboarding_results['count'],
        'reputation_alerts': reputation_results['alerts'],
        'new_alerts': alert_results['count'],
        'timestamp': str(datetime.now())
    }

def process_onboarding_queue():
    """Process pending onboarding applications"""
    client = bigquery.Client()
    genai = GenAIExplainer(PROJECT_ID)
    
    # Find merchants needing risk assessment
    query = """
    SELECT merchant_id, risk_score
    FROM `brand_risk_engine.onboarding`
    WHERE risk_score IS NULL OR explain_text = 'Initial processing'
    LIMIT 50
    """
    
    results = client.query(query).to_dataframe()
    processed_count = 0
    
    for _, row in results.iterrows():
        merchant_id = row['merchant_id']
        
        try:
            # Generate GenAI explanation
            explanation = genai.generate_onboarding_explanation(merchant_id)
            
            # Update merchant record
            update_query = f"""
            UPDATE `brand_risk_engine.onboarding`
            SET 
                explain_text = '{explanation}',
                updated_at = CURRENT_TIMESTAMP()
            WHERE merchant_id = '{merchant_id}'
            """
            
            client.query(update_query)
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing merchant {merchant_id}: {e}")
    
    return {'count': processed_count}

def check_reputation_alerts():
    """Check for reputation-based alerts"""
    client = bigquery.Client()
    genai = GenAIExplainer(PROJECT_ID)
    
    # Find high-risk reputation situations
    query = """
    SELECT merchant_id, max_reputation_risk, volume_spike_count
    FROM `brand_risk_engine.reputation_risk_summary`
    WHERE max_reputation_risk >= 0.7 OR volume_spike_count > 0
    """
    
    results = client.query(query).to_dataframe()
    alerts_generated = []
    
    for _, row in results.iterrows():
        merchant_id = row['merchant_id']
        
        try:
            # Generate PR brief
            pr_brief = genai.generate_pr_brief(merchant_id)
            
            # Create alert record
            alert_id = f"pr_{merchant_id}_{int(time.time())}"
            
            # Check if alert already exists
            check_query = f"""
            SELECT COUNT(*) as count
            FROM `brand_risk_engine.pr_alerts`
            WHERE merchant_id = '{merchant_id}' AND status = 'ACTIVE'
            """
            
            existing = client.query(check_query).to_dataframe()
            
            if existing.iloc[0]['count'] == 0:
                # Insert new alert
                insert_query = f"""
                INSERT INTO `brand_risk_engine.pr_alerts`
                (alert_id, merchant_id, alert_type, trigger_event, pr_brief, severity, status)
                VALUES (
                    '{alert_id}',
                    '{merchant_id}',
                    'reputation_crisis',
                    'high_risk_detected',
                    '{pr_brief.replace("'", "''")}',
                    'HIGH',
                    'ACTIVE'
                )
                """
                
                client.query(insert_query)
                alerts_generated.append(alert_id)
                
                # Send to alert channel
                send_alert_notification(alert_id, merchant_id, pr_brief)
                
        except Exception as e:
            logger.error(f"Error creating alert for {merchant_id}: {e}")
    
    return {'alerts': alerts_generated}

def update_aggregated_risk():
    """Update aggregated risk table"""
    client = bigquery.Client()
    
    # Recalculate aggregated risk
    query = """
    CREATE OR REPLACE TABLE `brand_risk_engine.aggregated_risk` AS
    SELECT 
        o.merchant_id,
        o.risk_score as onboarding_risk,
        COALESCE(r.avg_reputation_risk, 0.0) as reputation_risk,
        GREATEST(
            o.risk_score, 
            COALESCE(r.avg_reputation_risk, 0.0)
        ) as combined_risk,
        CASE 
            WHEN GREATEST(o.risk_score, COALESCE(r.avg_reputation_risk, 0.0)) >= 0.7 THEN 'HIGH'
            WHEN GREATEST(o.risk_score, COALESCE(r.avg_reputation_risk, 0.0)) >= 0.4 THEN 'MEDIUM'
            ELSE 'LOW'
        END as risk_level,
        CURRENT_TIMESTAMP() as last_updated
    FROM `brand_risk_engine.onboarding` o
    LEFT JOIN `brand_risk_engine.reputation_risk_summary` r 
        ON o.merchant_id = r.merchant_id
    WHERE o.merchant_id IS NOT NULL
    """
    
    client.query(query)
    logger.info("Aggregated risk table updated")

def generate_alerts():
    """Generate system alerts for high-risk situations"""
    client = bigquery.Client()
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, 'risk-alerts')
    
    # Find critical situations
    query = """
    SELECT merchant_id, combined_risk, risk_level
    FROM `brand_risk_engine.aggregated_risk`
    WHERE risk_level = 'HIGH'
    AND merchant_id NOT IN (
        SELECT merchant_id FROM `brand_risk_engine.pr_alerts`
        WHERE status = 'ACTIVE' AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    )
    """
    
    results = client.query(query).to_dataframe()
    alert_count = 0
    
    for _, row in results.iterrows():
        alert_message = {
            'alert_type': 'HIGH_RISK_MERCHANT',
            'merchant_id': row['merchant_id'],
            'risk_score': float(row['combined_risk']),
            'timestamp': datetime.now().isoformat(),
            'action_required': 'immediate_review'
        }
        
        # Publish to Pub/Sub
        publisher.publish(topic_path, json.dumps(alert_message).encode('utf-8'))
        alert_count += 1
    
    return {'count': alert_count}

def send_alert_notification(alert_id, merchant_id, pr_brief):
    """Send alert to notification channels"""
    try:
        # For demo: just log (in production: send to Slack, email, etc.)
        logger.info(f"🚨 ALERT {alert_id}: {merchant_id}")
        logger.info(f"PR Brief: {pr_brief[:100]}...")
        
        # You could integrate with:
        # - Slack API
        # - Email notifications
        # - PagerDuty
        # - Teams webhooks
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

if __name__ == '__main__':
    import os
    from datetime import datetime
    import time
    
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    
    # For local testing
    result = run_full_pipeline()
    print(json.dumps(result, indent=2))