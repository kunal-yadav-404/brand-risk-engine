#!/bin/bash

# Create bucket for Dataflow staging
gsutil mb gs://brand-risk-temp
gsutil mb gs://brand-risk-documents

# Set lifecycle rules
echo '{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 30}
    }
  ]
}' > lifecycle.json

gsutil lifecycle set lifecycle.json gs://brand-risk-temp