-- Create views for easier Looker Studio integration

-- Merchant Risk Overview View
CREATE VIEW `brand_risk_engine.merchant_risk_overview` AS
SELECT 
  merchant_id,
  name,
  website,
  risk_score,
  CASE 
    WHEN risk_score >= 0.7 THEN 'HIGH'
    WHEN risk_score >= 0.4 THEN 'MEDIUM'
    ELSE 'LOW'
  END as risk_level,
  explain_text,
  updated_at
FROM `brand_risk_engine.onboarding`
WHERE merchant_id IS NOT NULL;

-- Reputation Trends View
CREATE VIEW `brand_risk_engine.reputation_trends` AS
SELECT 
  merchant_id,
  source,
  DATE(timestamp) as mention_date,
  AVG(sentiment) as avg_sentiment,
  COUNT(*) as mention_count
FROM `brand_risk_engine.reputation`
WHERE merchant_id IS NOT NULL
GROUP BY merchant_id, source, DATE(timestamp);

-- Combined Risk Dashboard View
CREATE VIEW `brand_risk_engine.dashboard_summary` AS
SELECT 
  ar.merchant_id,
  o.name,
  ar.onboarding_risk,
  ar.reputation_risk,
  ar.combined_risk,
  ar.risk_level,
  ar.last_updated,
  o.website
FROM `brand_risk_engine.aggregated_risk` ar
LEFT JOIN `brand_risk_engine.onboarding` o 
  ON ar.merchant_id = o.merchant_id;
