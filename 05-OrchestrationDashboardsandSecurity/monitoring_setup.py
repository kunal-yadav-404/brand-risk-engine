# monitoring_setup.py
from google.cloud import monitoring_v3
import time

def create_monitoring_alerts():
    """Create monitoring alerts for the system"""
    
    client = monitoring_v3.AlertPolicyServiceClient()
    project_name = f"projects/{PROJECT_ID}"
    
    # Alert for high error rate in Dataflow
    dataflow_alert = monitoring_v3.AlertPolicy(
        display_name="Brand Risk Engine - Dataflow Errors",
        conditions=[
            monitoring_v3.AlertPolicy.Condition(
                display_name="Dataflow job errors",
                condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                    filter='resource.type="dataflow_job"',
                    comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                    threshold_value=monitoring_v3.TypedValue(double_value=5.0),
                    duration={"seconds": 300}
                )
            )
        ],
        alert_strategy=monitoring_v3.AlertPolicy.AlertStrategy(
            auto_close={"seconds": 86400}  # 24 hours
        ),
        enabled=True
    )
    
    # Alert for GenAI processing delays
    genai_alert = monitoring_v3.AlertPolicy(
        display_name="Brand Risk Engine - GenAI Processing Delays",
        conditions=[
            monitoring_v3.AlertPolicy.Condition(
                display_name="GenAI response time high",
                condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                    filter='resource.type="cloud_function"',
                    comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                    threshold_value=monitoring_v3.TypedValue(double_value=30.0),
                    duration={"seconds": 300}
                )
            )
        ],
        enabled=True
    )
    
    # Create the alerts
    client.create_alert_policy(name=project_name, alert_policy=dataflow_alert)
    client.create_alert_policy(name=project_name, alert_policy=genai_alert)
    
    print("Monitoring alerts created successfully")

if __name__ == '__main__':
    import os
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    create_monitoring_alerts()