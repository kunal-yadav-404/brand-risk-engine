# main.py (simplified working version)
import functions_framework
from google.cloud import bigquery
from google.cloud import pubsub_v1
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.http
def orchestrate_risk_pipeline(request):
    """Main orchestration function"""
    try:
        # Handle CORS
        if request.method == 'OPTIONS':
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '3600'
            }
            return ('', 204, headers)

        # Set CORS headers for actual request
        headers = {'Access-Control-Allow-Origin': '*'}
        
        # Get request data
        request_json = request.get_json(silent=True) or {}
        action = request_json.get('action', 'health_check')
        
        logger.info(f"Orchestration request: {action}")
        
        if action == 'health_check':
            result = perform_health_check()
        elif action == 'update_risk':
            result = update_aggregated_risk()
        elif action == 'check_alerts':
            result = check_active_alerts()
        else:
            result = {'error': 'Unknown action', 'available_actions': ['health_check', 'update_risk', 'check_alerts']}
            
        return (json.dumps(result), 200, headers)
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        error_result = {'error': str(e), 'timestamp': datetime.now().isoformat()}
        return (json.dumps(error_result), 500, {'Access-Control-Allow-Origin': '*'})

def perform_health_check():
    """Perform system health check"""
    client = bigquery.Client()
    
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'components': {}
    }
    
    try:
        # Check onboarding data
        query = """
        SELECT 
            COUNT(*) as total_merchants,
            COUNT(CASE WHEN updated_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) THEN 1 END) as recent_updates,
            ROUND(AVG(COALESCE(risk_score, 0)), 3) as avg_risk
        FROM `brand_risk_engine.onboarding`
        """
        
        result = client.query(query).to_dataframe()
        if not result.empty:
            health_status['components']['onboarding'] = {
                'total_merchants': int(result.iloc[0]['total_merchants']),
                'recent_updates': int(result.iloc[0]['recent_updates']),
                'avg_risk': float(result.iloc[0]['avg_risk']),
                'status': 'healthy'
            }
        else:
            health_status['components']['onboarding'] = {'status': 'no_data'}
            
    except Exception as e:
        health_status['components']['onboarding'] = {'status': 'error', 'error': str(e)}
        health_status['status'] = 'warning'
    
    try:
        # Check reputation data
        query = """
        SELECT 
            COUNT(*) as total_mentions,
            COUNT(CASE WHEN timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) THEN 1 END) as recent_mentions,
            ROUND(AVG(sentiment), 3) as avg_sentiment
        FROM `brand_risk_engine.reputation`
        """
        
        result = client.query(query).to_dataframe()
        if not result.empty:
            health_status['components']['reputation'] = {
                'total_mentions': int(result.iloc[0]['total_mentions']),
                'recent_mentions': int(result.iloc[0]['recent_mentions']),
                'avg_sentiment': float(result.iloc[0]['avg_sentiment']) if result.iloc[0]['avg_sentiment'] else 0.0,
                'status': 'healthy'
            }
        else:
            health_status['components']['reputation'] = {'status': 'no_data'}
            
    except Exception as e:
        health_status['components']['reputation'] = {'status': 'error', 'error': str(e)}
        health_status['status'] = 'warning'
    
    return health_status

def update_aggregated_risk():
    """Update aggregated risk calculations"""
    client = bigquery.Client()
    
    try:
        # Update aggregated risk table
        query = """
        CREATE OR REPLACE TABLE `brand_risk_engine.aggregated_risk` AS
        SELECT 
            o.merchant_id,
            COALESCE(o.risk_score, 0.0) as onboarding_risk,
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
        
        job = client.query(query)
        job.result()  # Wait for completion
        
        # Count results
        count_query = "SELECT COUNT(*) as updated_count FROM `brand_risk_engine.aggregated_risk`"
        count_result = client.query(count_query).to_dataframe()
        
        return {
            'status': 'success',
            'updated_merchants': int(count_result.iloc[0]['updated_count']),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def check_active_alerts():
    """Check for active alerts"""
    client = bigquery.Client()
    
    try:
        # Check for high-risk situations
        query = """
        SELECT 
            COUNT(*) as high_risk_merchants,
            COUNT(CASE WHEN combined_risk >= 0.8 THEN 1 END) as critical_merchants
        FROM `brand_risk_engine.aggregated_risk`
        WHERE risk_level IN ('HIGH', 'MEDIUM')
        """
        
        result = client.query(query).to_dataframe()
        
        # Check active PR alerts
        alerts_query = """
        SELECT 
            COUNT(*) as active_alerts,
            COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_severity_alerts
        FROM `brand_risk_engine.pr_alerts`
        WHERE status = 'ACTIVE'
        """
        
        alerts_result = client.query(alerts_query).to_dataframe()
        
        return {
            'status': 'success',
            'high_risk_merchants': int(result.iloc[0]['high_risk_merchants']) if not result.empty else 0,
            'critical_merchants': int(result.iloc[0]['critical_merchants']) if not result.empty else 0,
            'active_alerts': int(alerts_result.iloc[0]['active_alerts']) if not alerts_result.empty else 0,
            'high_severity_alerts': int(alerts_result.iloc[0]['high_severity_alerts']) if not alerts_result.empty else 0,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }