#!/bin/bash

# Create VPC
gcloud compute networks create brand-risk-vpc --subnet-mode=custom

# Create subnet
gcloud compute networks subnets create brand-risk-subnet \
  --network=brand-risk-vpc \
  --range=10.0.0.0/24 \
  --region=$REGION

# Create firewall rules
gcloud compute firewall-rules create allow-internal \
  --network=brand-risk-vpc \
  --allow=tcp,udp,icmp \
  --source-ranges=10.0.0.0/8

# Private Service Connect (for Google APIs)
gcloud compute addresses create google-apis-range \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=brand-risk-vpc

gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-apis-range \
  --network=brand-risk-vpc