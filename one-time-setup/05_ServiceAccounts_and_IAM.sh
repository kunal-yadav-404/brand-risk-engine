#!/bin/bash

# Create service accounts
gcloud iam service-accounts create dataflow-runner \
  --display-name="Dataflow Runner"

gcloud iam service-accounts create bigquery-writer \
  --display-name="BigQuery Writer"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:dataflow-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/dataflow.worker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:bigquery-writer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"