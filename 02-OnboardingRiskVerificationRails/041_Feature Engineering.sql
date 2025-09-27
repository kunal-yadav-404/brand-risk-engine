-- Create feature store table
CREATE TABLE `brand_risk_engine.onboarding_features` AS
WITH base_features AS (
  SELECT 
    merchant_id,
    name,
    website,
    domain_age,
    JSON_EXTRACT_SCALAR(contact_info, '$.email') as email,
    document_status,
    verification_score,
    
    -- Domain features
    CASE 
      WHEN domain_age >= 365 THEN 1.0
      WHEN domain_age >= 90 THEN 0.7
      WHEN domain_age >= 30 THEN 0.4
      ELSE 0.0
    END as domain_age_score,
    
    -- Email domain match
    CASE 
      WHEN REGEXP_EXTRACT(website, r'https?://(?:www\.)?([^/]+)') = 
           REGEXP_EXTRACT(JSON_EXTRACT_SCALAR(contact_info, '$.email'), r'@(.+)') 
      THEN 1.0 
      ELSE 0.0 
    END as email_domain_match,
    
    -- Document verification
    CASE document_status
      WHEN 'verified' THEN 1.0
      WHEN 'uploaded' THEN 0.5
      ELSE 0.0
    END as doc_verification_score,
    
    -- Website accessibility
    CASE 
      WHEN website IS NOT NULL AND LENGTH(website) > 10 THEN 1.0
      ELSE 0.0
    END as website_present,
    
    created_at
  FROM `brand_risk_engine.onboarding`
),
external_features AS (
  SELECT 
    merchant_id,
    -- Add features from domain checker results
    0.8 as ssl_score,  -- Will be populated by domain checker
    0.9 as content_quality_score,
    0.0 as blacklist_risk
  FROM `brand_risk_engine.onboarding`
)
SELECT 
  bf.*,
  ef.ssl_score,
  ef.content_quality_score,
  ef.blacklist_risk,
  
  -- Composite risk features
  (bf.domain_age_score + bf.email_domain_match + bf.doc_verification_score + 
   bf.website_present + ef.ssl_score + ef.content_quality_score - ef.blacklist_risk) / 6 
   as composite_trust_score
   
FROM base_features bf
JOIN external_features ef ON bf.merchant_id = ef.merchant_id;