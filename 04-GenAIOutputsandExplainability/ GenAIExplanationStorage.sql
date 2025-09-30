-- Create table for GenAI outputs
CREATE TABLE `brand_risk_engine.genai_explanations` (
  merchant_id STRING NOT NULL,
  explanation_type STRING, -- 'onboarding' or 'pr_brief'
  generated_text STRING,
  risk_score FLOAT64,
  trigger_event STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  model_version STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY merchant_id;

-- Create PR alerts table
CREATE TABLE `brand_risk_engine.pr_alerts` (
  alert_id STRING NOT NULL,
  merchant_id STRING,
  alert_type STRING,
  trigger_event STRING,
  pr_brief STRING,
  severity STRING,
  status STRING DEFAULT 'ACTIVE',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  acknowledged_at TIMESTAMP,
  acknowledged_by STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY merchant_id;