-- Create dataset
CREATE SCHEMA `brand_risk_engine`
OPTIONS(
  description="Brand Risk Engine Data",
  location="US"
);

-- Onboarding table
CREATE TABLE `brand_risk_engine.onboarding` (
  merchant_id STRING NOT NULL,
  name STRING,
  website STRING,
  domain_age INT64,
  contact_info JSON,
  document_status STRING,
  verification_score FLOAT64,
  risk_score FLOAT64,
  explain_text STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY merchant_id;

-- Reputation table
CREATE TABLE `brand_risk_engine.reputation` (
  merchant_id STRING,
  source STRING,
  mention_id STRING NOT NULL,
  text STRING,
  sentiment FLOAT64,
  timestamp TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(timestamp)
CLUSTER BY merchant_id, source;

-- Aggregated risk table
CREATE TABLE `brand_risk_engine.aggregated_risk` (
  merchant_id STRING NOT NULL,
  onboarding_risk FLOAT64,
  reputation_risk FLOAT64,
  combined_risk FLOAT64,
  risk_level STRING,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY merchant_id;