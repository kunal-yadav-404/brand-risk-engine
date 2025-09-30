-- Enhanced merchant overview with GenAI explanations
CREATE OR REPLACE VIEW `brand_risk_engine.enhanced_merchant_overview` AS
SELECT 
  o.merchant_id,
  o.name,
  o.website,
  o.risk_score,
  ar.risk_level,
  o.explain_text,
  ge.generated_text as genai_explanation,
  o.updated_at,
  CASE 
    WHEN ar.risk_level = 'HIGH' THEN 3
    WHEN ar.risk_level = 'MEDIUM' THEN 2
    ELSE 1
  END as risk_priority
FROM `brand_risk_engine.onboarding` o
LEFT JOIN `brand_risk_engine.aggregated_risk` ar ON o.merchant_id = ar.merchant_id
LEFT JOIN `brand_risk_engine.genai_explanations` ge 
  ON o.merchant_id = ge.merchant_id AND ge.explanation_type = 'onboarding';

-- PR dashboard view
CREATE OR REPLACE VIEW `brand_risk_engine.pr_dashboard` AS
SELECT 
  pa.alert_id,
  pa.merchant_id,
  o.name as merchant_name,
  pa.severity,
  pa.status,
  pa.pr_brief,
  pa.created_at,
  DATETIME_DIFF(CURRENT_DATETIME(), DATETIME(pa.created_at), HOUR) as hours_since_alert,
  CASE 
    WHEN pa.status = 'ACTIVE' AND DATETIME_DIFF(CURRENT_DATETIME(), DATETIME(pa.created_at), HOUR) > 2 THEN 'OVERDUE'
    WHEN pa.status = 'ACTIVE' THEN 'PENDING'
    ELSE pa.status
  END as alert_status
FROM `brand_risk_engine.pr_alerts` pa
LEFT JOIN `brand_risk_engine.onboarding` o ON pa.merchant_id = o.merchant_id
WHERE pa.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY);

-- Real-time monitoring view
CREATE OR REPLACE VIEW `brand_risk_engine.realtime_monitoring` AS
WITH recent_activity AS (
  SELECT 
    'reputation' as data_type,
    merchant_id,
    COUNT(*) as record_count,
    AVG(sentiment) as avg_sentiment,
    MAX(timestamp) as last_activity
  FROM `brand_risk_engine.reputation`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  GROUP BY merchant_id
  
  UNION ALL
  
  SELECT 
    'onboarding' as data_type,
    merchant_id,
    COUNT(*) as record_count,
    AVG(risk_score) as avg_sentiment,
    MAX(updated_at) as last_activity
  FROM `brand_risk_engine.onboarding`
  WHERE updated_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  GROUP BY merchant_id
)
SELECT 
  data_type,
  COUNT(DISTINCT merchant_id) as active_merchants,
  SUM(record_count) as total_records,
  AVG(avg_sentiment) as overall_sentiment,
  MAX(last_activity) as latest_activity
FROM recent_activity
GROUP BY data_type;