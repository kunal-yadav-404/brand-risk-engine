#!/bin/bash

# Set variables
export PROJECT_ID="brand-risk-engine-$(date +%s)"
export REGION="us-central1"
export ZONE="us-central1-a"
export BILLING_ACCOUNT_ID="014C68-A56BC6-283865" 

# Create project
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# --- NEW BILLING COMMANDS ADDED HERE ---

# 1. Enable the Cloud Billing API (often needed before linking)
gcloud services enable cloudbilling.googleapis.com

# 2. Link the new project to your existing billing account
echo "Linking project $PROJECT_ID to billing account $BILLING_ACCOUNT_ID..."
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID

# Enable APIs
gcloud services enable \
  compute.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com \
  dataflow.googleapis.com \
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  servicenetworking.googleapis.com