#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Configuration (Change these if necessary)
PROJECT_ID="sascha-playground-doit"
REGION="us-central1"
DATASET_NAME="vertex_ai_logs"
TABLE_NAME="gemini_logs"
WINDOW_MINUTES="10"
TOKEN_THRESHOLD="5000"

# Resource Names
FUNCTION_NAME="vertex-ai-log-monitor"
SCHEDULER_JOB_NAME="vertex-ai-log-monitor-job"
SA_NAME="vertex-log-monitor-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Deploying Vertex AI Request/Response Monitor to Project: $PROJECT_ID"

# 1. Create a dedicated Service Account for the Cloud Function (if it doesn't exist)
echo "Creating Service Account: $SA_NAME..."
gcloud iam service-accounts create $SA_NAME --description="Service account for Vertex AI log monitoring Cloud Function" --display-name="Vertex Log Monitor SA" --project=$PROJECT_ID || echo "Service account may already exist, proceeding..."

# 2. Grant permissions to the Service Account
# Needs BigQuery Data Viewer to read the logs and Job User to run the query
echo "Granting BigQuery roles to Service Account..."
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/bigquery.dataViewer" --condition=None >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/bigquery.jobUser" --condition=None >/dev/null

# 3. Deploy the Cloud Function
echo "Deploying Cloud Function: $FUNCTION_NAME..."
gcloud functions deploy $FUNCTION_NAME --gen2 --region=$REGION --project=$PROJECT_ID --runtime=python311 --source=./cloud_function --entry-point=check_vertex_usage --trigger-http --no-allow-unauthenticated --service-account=$SA_EMAIL --set-env-vars=PROJECT_ID=$PROJECT_ID,DATASET_NAME=$DATASET_NAME,TABLE_NAME=$TABLE_NAME,WINDOW_MINUTES=$WINDOW_MINUTES,TOKEN_THRESHOLD=$TOKEN_THRESHOLD

# Get the URL of the deployed function
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --project=$PROJECT_ID --format="value(serviceConfig.uri)")

echo "Cloud Function deployed successfully at: $FUNCTION_URL"

# 4. Create Cloud Scheduler Job
echo "Creating Cloud Scheduler Job: $SCHEDULER_JOB_NAME..."
# Enable Cloud Scheduler API if not enabled
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID || true

# Check if the job already exists, if so, update it. Otherwise, create it.
if gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Job exists, updating..."
    gcloud scheduler jobs update http $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID --schedule="*/$WINDOW_MINUTES * * * *" --uri=$FUNCTION_URL --http-method=GET --oidc-service-account-email=$SA_EMAIL
else
    echo "Creating new job..."
    gcloud scheduler jobs create http $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID --schedule="*/$WINDOW_MINUTES * * * *" --uri=$FUNCTION_URL --http-method=GET --oidc-service-account-email=$SA_EMAIL
fi

echo "Deployment Complete!"
echo "The monitor will run every $WINDOW_MINUTES minutes."
