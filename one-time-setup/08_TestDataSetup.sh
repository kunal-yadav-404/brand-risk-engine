#!/bin/bash

# Test onboarding message
gcloud pubsub topics publish onboarding-stream \
  --message='{"merchant_id":"TEST001","name":"Test Merchant","website":"https://test.com","domain_age":365,"contact_info":{"email":"test@test.com"},"document_status":"uploaded"}'

# Test reputation message
gcloud pubsub topics publish reputation-stream \
  --message='{"merchant_id":"TEST001","source":"twitter","mention_id":"tweet123","text":"Great service from Test Merchant","sentiment":0.8,"timestamp":"2024-01-01T10:00:00Z"}'