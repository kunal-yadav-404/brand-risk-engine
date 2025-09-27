#!/bin/bash

echo "Setting up Looker Studio skeleton..."

# Create sample data for testing
bq query --use_legacy_sql=false "
INSERT INTO \`brand_risk_engine.onboarding\` 
(merchant_id, name, website, domain_age, contact_info, document_status, verification_score, risk_score, explain_text)
VALUES 
('DEMO001', 'Demo Merchant 1', 'https://demo1.com', 365, '{\"email\":\"demo1@test.com\"}', 'verified', 0.8, 0.3, 'Low risk merchant'),
('DEMO002', 'Demo Merchant 2', 'https://demo2.com', 30, '{\"email\":\"demo2@test.com\"}', 'pending', 0.4, 0.8, 'High risk - new domain'),
('DEMO003', 'Demo Merchant 3', 'https://demo3.com', 200, '{\"email\":\"demo3@test.com\"}', 'verified', 0.9, 0.1, 'Very low risk merchant')
"

bq query --use_legacy_sql=false "
INSERT INTO \`brand_risk_engine.reputation\` 
(merchant_id, source, mention_id, text, sentiment, timestamp)
VALUES 
('DEMO001', 'twitter', 'tweet001', 'Great service!', 0.9, CURRENT_TIMESTAMP()),
('DEMO002', 'news', 'news001', 'Questionable practices reported', -0.7, CURRENT_TIMESTAMP()),
('DEMO003', 'reviews', 'review001', 'Excellent experience', 0.8, CURRENT_TIMESTAMP())
"

bq query --use_legacy_sql=false "
INSERT INTO \`brand_risk_engine.aggregated_risk\` 
(merchant_id, onboarding_risk, reputation_risk, combined_risk, risk_level)
VALUES 
('DEMO001', 0.3, 0.1, 0.2, 'LOW'),
('DEMO002', 0.8, 0.7, 0.75, 'HIGH'),
('DEMO003', 0.1, 0.2, 0.15, 'LOW')
"

echo "Sample data created. You can now connect Looker Studio to:"
echo "Project: $PROJECT_ID"
echo "Dataset: brand_risk_engine"
echo "Views: merchant_risk_overview, reputation_trends, dashboard_summary"
