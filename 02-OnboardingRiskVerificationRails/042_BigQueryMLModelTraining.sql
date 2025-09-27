-- Create training dataset with labels
CREATE TABLE `brand_risk_engine.training_data` AS
WITH labeled_data AS (
  SELECT 
    *,
    -- Synthetic labels for demo (in production, use historical fraud data)
    CASE 
      WHEN composite_trust_score >= 0.8 THEN 'LOW_RISK'
      WHEN composite_trust_score >= 0.5 THEN 'MEDIUM_RISK'
      ELSE 'HIGH_RISK'
    END as risk_label,
    
    CASE 
      WHEN composite_trust_score >= 0.8 THEN 0
      WHEN composite_trust_score >= 0.5 THEN 1
      ELSE 2
    END as risk_score_numeric
  FROM `brand_risk_engine.onboarding_features`
)
SELECT * FROM labeled_data;

-- Train BigQuery ML model
CREATE OR REPLACE MODEL `brand_risk_engine.onboarding_risk_model`
OPTIONS(
  model_type='BOOSTED_TREE_CLASSIFIER',
  input_label_cols=['risk_label'],
  max_iterations=100,
  learn_rate=0.1,
  subsample=0.8
) AS
SELECT
  domain_age_score,
  email_domain_match,
  doc_verification_score,
  website_present,
  ssl_score,
  content_quality_score,
  blacklist_risk,
  composite_trust_score,
  risk_label
FROM `brand_risk_engine.training_data`;

-- Evaluate model
SELECT * FROM ML.EVALUATE(MODEL `brand_risk_engine.onboarding_risk_model`);

-- Create prediction function
CREATE OR REPLACE FUNCTION `brand_risk_engine.predict_merchant_risk`(
  domain_age_score FLOAT64,
  email_domain_match FLOAT64,
  doc_verification_score FLOAT64,
  website_present FLOAT64,
  ssl_score FLOAT64,
  content_quality_score FLOAT64,
  blacklist_risk FLOAT64,
  composite_trust_score FLOAT64
)
RETURNS STRUCT<predicted_risk STRING, confidence FLOAT64>
LANGUAGE SQL AS (
  (
    SELECT AS STRUCT
      predicted_risk_label as predicted_risk,
      ROUND(predicted_risk_label_probs[OFFSET(0)].prob, 3) as confidence
    FROM ML.PREDICT(
      MODEL `brand_risk_engine.onboarding_risk_model`,
      (SELECT 
        domain_age_score,
        email_domain_match,
        doc_verification_score,
        website_present,
        ssl_score,
        content_quality_score,
        blacklist_risk,
        composite_trust_score
      )
    )
  )
);