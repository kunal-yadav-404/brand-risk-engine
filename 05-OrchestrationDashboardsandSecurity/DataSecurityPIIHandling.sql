-- Create secure views with PII masking
CREATE OR REPLACE VIEW `brand_risk_engine.secure_onboarding` AS
SELECT 
  merchant_id,
  name,
  website,
  domain_age,
  -- Mask sensitive contact info
  CASE 
    WHEN JSON_EXTRACT_SCALAR(contact_info, '$.email') IS NOT NULL 
    THEN CONCAT(LEFT(JSON_EXTRACT_SCALAR(contact_info, '$.email'), 3), '***@***.com')
    ELSE 'No email'
  END as masked_email,
  document_status,
  verification_score,
  risk_score,
  explain_text,
  updated_at
FROM `brand_risk_engine.onboarding`;

-- Create audit log table
CREATE TABLE `brand_risk_engine.access_audit` (
  access_id STRING NOT NULL,
  user_email STRING,
  merchant_id STRING,
  data_accessed STRING,
  access_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  ip_address STRING,
  user_agent STRING
)
PARTITION BY DATE(access_timestamp);

-- Data retention policy
CREATE OR REPLACE VIEW `brand_risk_engine.data_retention_policy` AS
SELECT 
  table_name,
  CASE table_name
    WHEN 'onboarding' THEN 2555  -- 7 years for compliance
    WHEN 'reputation' THEN 1095  -- 3 years for reputation data
    WHEN 'pr_alerts' THEN 365    -- 1 year for alerts
    ELSE 730                     -- 2 years default
  END as retention_days
FROM INFORMATION_SCHEMA.TABLES 
WHERE table_schema = 'brand_risk_engine';