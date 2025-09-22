#!/bin/bash

# Create topics
gcloud pubsub topics create onboarding-stream
gcloud pubsub topics create reputation-stream
gcloud pubsub topics create risk-alerts

# Create subscriptions
gcloud pubsub subscriptions create onboarding-dataflow-sub \
  --topic=onboarding-stream

gcloud pubsub subscriptions create reputation-dataflow-sub \
  --topic=reputation-stream

gcloud pubsub subscriptions create alerts-sub \
  --topic=risk-alerts