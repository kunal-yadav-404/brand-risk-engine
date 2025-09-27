# First, ensure BigQuery connector permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:looker-studio@system.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
