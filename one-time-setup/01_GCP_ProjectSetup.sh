#!/bin/bash

# Set variables
export PROJECT_ID="brand-risk-engine-$(date +%s)"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create project
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable \
  compute.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com \
  dataflow.googleapis.com \
  aiplatform.googleapis.com \
  documentai.googleapis.com \
  servicenetworking.googleapis.com