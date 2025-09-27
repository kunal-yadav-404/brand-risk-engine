# First, ensure BigQuery connector permissions
gcloud iam service-accounts create looker-studio \
  --display-name="Looker Studio"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:looker-studio@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# gcloud projects add-iam-policy-binding $PROJECT_ID \
#   --member="serviceAccount:service-768479878595@gcp-sa-looker-studio.iam.gserviceaccount.com" \
#   --role="roles/bigquery.dataViewer"
