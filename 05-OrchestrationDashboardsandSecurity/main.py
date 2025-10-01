# main.py (Cloud Function)
import functions_framework
import json
import logging
import os
import time
from datetime import datetime
# External dependencies
from google.cloud import pubsub_v1
from google.cloud import bigquery
import pandas as pd

# NOTE: Assuming genai_explainer is a custom library or a module in the same directory.
from genai_explainer import GenAIExplainer

# --- Configuration ---
# For Cloud Functions, GOOGLE_CLOUD_PROJECT is usually set automatically. 
# Provide a fallback for local execution.
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'YOUR_PROJECT_ID_HERE')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def orchestrate_risk_pipeline(request):
    """
    Main orchestration function, triggered by HTTP (e.g., Cloud Scheduler).
    Expects a JSON body with an 'action' key (e.g., 'full_pipeline').
    """
    try:
        # Get request data. If not JSON, get_json() returns None.
        request_data = request.get_json(silent=True)
        
        # Determine action, default to 'full_pipeline'
        if request_data:
            action = request_data.get('action', 'full_pipeline')
        else:
            action = 'full_pipeline' # Default action if no JSON or invalid JSON
            
        logger.info(f"Starting orchestration with action: {action}")
        
        # Route execution based on action
        if action == 'full_pipeline':
            result = run_full_pipeline()
        elif action == 'reputation_check':
            result = check_reputation_alerts()
        elif action == 'onboarding_review':
            # Note: This calls process_onboarding_queue, which handles the review logic.
            result = process_onboarding_queue()
        else:
            result = {'error': f'Unknown action: {action}'}
            logger.warning(f"Unknown action requested: {action}")
            return {'error': f'Unknown action: {action}'}, 400
            
        return result, 200
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}", exc_info=True)
        return {'error': f"Internal Server Error: {str(e)}"}, 500

# --- Pipeline Steps ---

def run_full_pipeline():
    """Execute complete risk assessment pipeline (Steps 1-4)"""
    logger.info("Starting full pipeline execution")
    
    # Step 1: Process pending onboarding (calls BigQuery and GenAI)
    onboarding_results = process_onboarding_queue()
    logger.info(f"Step 1: Processed {onboarding_results['count']} onboarding records.")
    
    # Step 2: Check reputation alerts (calls BigQuery and GenAI)
    reputation_results = check_reputation_alerts()
    logger.info(f"Step 2: Generated {len(reputation_results['alerts'])} reputation alerts.")
    
    # Step 3: Update aggregated risk (calls BigQuery DDL)
    update_aggregated_risk()
    logger.info("Step 3: Aggregated risk table updated.")
    
    # Step 4: Generate general alerts (calls BigQuery and Pub/Sub)
    alert_results = generate_alerts()
    logger.info(f"Step 4: Published {alert_results['count']} new system alerts.")
    
    return {
        'status': 'completed',
        'onboarding_processed': onboarding_results['count'],
        'reputation_alerts': len(reputation_results['alerts']),
        'new_system_alerts': alert_results['count'],
        'timestamp': datetime.now().isoformat()
    }

def process_onboarding_queue():
    """Process pending onboarding applications (Step 1)"""
    client = bigquery.Client(project=PROJECT_ID)
    genai = GenAIExplainer(PROJECT_ID) # Assumes GenAIExplainer handles auth internally
    
    logger.info("Querying for merchants needing risk assessment...")
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
            # Generate GenAI explanation (Placeholder for actual GenAI call)
            explanation = genai.generate_onboarding_explanation(merchant_id)
            
            # Update merchant record (Using DML with parameterized query for safety)
            update_query = """
            UPDATE `brand_risk_engine.onboarding`
            SET 
                explain_text = @explanation,
                updated_at = CURRENT_TIMESTAMP()
            WHERE merchant_id = @merchant_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("explanation", "STRING", explanation),
                    bigquery.ScalarQueryParameter("merchant_id", "STRING", merchant_id),
                ]
            )
            
            client.query(update_query, job_config=job_config).result()
            processed_count += 1
            logger.info(f"Updated onboarding risk for merchant: {merchant_id}")
            
        except Exception as e:
            logger.error(f"Error processing merchant {merchant_id}: {e}", exc_info=True)
    
    return {'count': processed_count}

def check_reputation_alerts():
    """Check for reputation-based alerts (Step 2)"""
    client = bigquery.Client(project=PROJECT_ID)
    genai = GenAIExplainer(PROJECT_ID)
    
    logger.info("Querying for high-risk reputation summary...")
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
            # Generate PR brief (Placeholder for actual GenAI call)
            pr_brief = genai.generate_pr_brief(merchant_id)
            
            # Check if alert already exists (Using parameterized query)
            check_query = """
            SELECT COUNT(*) as count
            FROM `brand_risk_engine.pr_alerts`
            WHERE merchant_id = @merchant_id AND status = 'ACTIVE'
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("merchant_id", "STRING", merchant_id),
                ]
            )
            
            existing = client.query(check_query, job_config=job_config).to_dataframe()
            
            if existing.iloc[0]['count'] == 0:
                # Insert new alert (Using DML with parameters to prevent SQL injection)
                insert_query = """
                INSERT INTO `brand_risk_engine.pr_alerts`
                (alert_id, merchant_id, alert_type, trigger_event, pr_brief, severity, status, created_at)
                VALUES (
                    @alert_id,
                    @merchant_id,
                    'reputation_crisis',
                    'high_risk_detected',
                    @pr_brief,
                    'HIGH',
                    'ACTIVE',
                    CURRENT_TIMESTAMP()
                )
                """
                alert_id = f"pr_{merchant_id}_{int(time.time())}"
                
                insert_job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("alert_id", "STRING", alert_id),
                        bigquery.ScalarQueryParameter("merchant_id", "STRING", merchant_id),
                        # Use a parameterized query to safely handle quotes in the brief
                        bigquery.ScalarQueryParameter("pr_brief", "STRING", pr_brief), 
                    ]
                )
                
                client.query(insert_query, job_config=insert_job_config).result()
                alerts_generated.append(alert_id)
                
                # Send to alert channel
                send_alert_notification(alert_id, merchant_id, pr_brief)
                logger.info(f"Generated new PR Alert: {alert_id} for {merchant_id}")
                
            else:
                logger.info(f"Active PR Alert already exists for {merchant_id}. Skipping new alert.")
                
        except Exception as e:
            logger.error(f"Error creating alert for {merchant_id}: {e}", exc_info=True)
    
    return {'alerts': alerts_generated}

def update_aggregated_risk():
    """Update aggregated risk table (Step 3)"""
    client = bigquery.Client(project=PROJECT_ID)
    
    logger.info("Executing aggregated risk table update (CTAS)...")
    # Recalculate aggregated risk using CREATE OR REPLACE TABLE AS SELECT (CTAS)
    query = """
    CREATE OR REPLACE TABLE `brand_risk_engine.aggregated_risk` AS
    SELECT 
        o.merchant_id,
        o.risk_score as onboarding_risk,
        COALESCE(r.avg_reputation_risk, 0.0) as reputation_risk,
        GREATEST(
            COALESCE(o.risk_score, 0.0), 
            COALESCE(r.avg_reputation_risk, 0.0)
        ) as combined_risk,
        CASE 
            WHEN GREATEST(COALESCE(o.risk_score, 0.0), COALESCE(r.avg_reputation_risk, 0.0)) >= 0.7 THEN 'HIGH'
            WHEN GREATEST(COALESCE(o.risk_score, 0.0), COALESCE(r.avg_reputation_risk, 0.0)) >= 0.4 THEN 'MEDIUM'
            ELSE 'LOW'
        END as risk_level,
        CURRENT_TIMESTAMP() as last_updated
    FROM `brand_risk_engine.onboarding` o
    LEFT JOIN `brand_risk_engine.reputation_risk_summary` r 
        ON o.merchant_id = r.merchant_id
    WHERE o.merchant_id IS NOT NULL
    """
    
    # Run the query and wait for completion
    client.query(query).result()
    logger.info("Aggregated risk table updated successfully.")

def generate_alerts():
    """Generate system alerts for high-risk situations (Step 4)"""
    client = bigquery.Client(project=PROJECT_ID)
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, 'risk-alerts')
    
    logger.info("Querying for new HIGH risk merchants...")
    # Find critical situations that don't have a recent PR alert
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
            # Ensure combined_risk is treated as a standard Python float before JSON serialization
            'risk_score': float(row['combined_risk']),
            'timestamp': datetime.now().isoformat(),
            'action_required': 'immediate_review'
        }
        
        # Publish to Pub/Sub
        publisher.publish(topic_path, json.dumps(alert_message).encode('utf-8'))
        alert_count += 1
        logger.info(f"Published system alert for high risk merchant: {row['merchant_id']}")
    
    return {'count': alert_count}

def send_alert_notification(alert_id, merchant_id, pr_brief):
    """Send alert to notification channels"""
    try:
        # For demo: just log (in production: send to Slack, email, etc.)
        logger.info(f"🚨 ALERT {alert_id}: {merchant_id}")
        logger.info(f"PR Brief Preview: {pr_brief[:100]}...")
        
        # You could integrate with external services here.
        
    except Exception as e:
        logger.error(f"Error sending notification for {merchant_id}: {e}", exc_info=True)

if __name__ == '__main__':
    # Override PROJECT_ID for local testing if GOOGLE_CLOUD_PROJECT is not set
    if PROJECT_ID == 'YOUR_PROJECT_ID_HERE':
        PROJECT_ID = 'local-testing-project'
        logger.warning(f"Using default PROJECT_ID: {PROJECT_ID}. Update this for real deployment.")
        
    # --- Local Testing Block ---
    logger.info(f"--- Running full pipeline locally in project: {PROJECT_ID} ---")
    
    # Mocking environment for GenAIExplainer if needed locally
    # Note: BigQuery calls will fail if not authenticated and tables don't exist.
    
    # result = run_full_pipeline()
    # print(json.dumps(result, indent=2))
