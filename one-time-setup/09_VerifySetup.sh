#!/bin/bash

# Check BigQuery tables
bq ls brand_risk_engine

# Check Pub/Sub topics
gcloud pubsub topics list

# Check if test messages are flowing
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `brand_risk_engine.onboarding`'