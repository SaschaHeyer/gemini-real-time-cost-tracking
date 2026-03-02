#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

# Configuration (Change these if necessary)
PROJECT_ID="sascha-playground-doit"
ALERT_NAME="Vertex AI Cost Anomaly Alert"

echo "Deploying Alerting Infrastructure to Project: $PROJECT_ID"

# 1. Create the Alerting Policy JSON definition
echo "Generating Alert Policy definition..."
cat << EOF > /tmp/vertex_ai_alert_policy.json
{
  "displayName": "$ALERT_NAME",
  "combiner": "OR",
  "conditions": [
    {
      "displayName": "Log match condition",
      "conditionMatchedLog": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"vertex-ai-log-monitor\" AND textPayload:\"HIGH VERTEX AI USAGE ALERT\""
      }
    }
  ],
  "alertStrategy": {
    "notificationRateLimit": {
      "period": "300s"
    }
  }
}
EOF

# 2. Apply the Alerting Policy
echo "Creating Alerting Policy in Cloud Monitoring..."
# We use the standard gcloud monitoring policies create command
gcloud monitoring policies create \
    --policy-from-file="/tmp/vertex_ai_alert_policy.json" \
    --project=$PROJECT_ID

echo "--------------------------------------------------------"
echo "✅ Alerting Policy created successfully!"
echo ""
echo "IMPORTANT: The policy exists, but it needs a Notification Channel (e.g., Email or Slack)."
echo "To attach a Notification Channel:"
echo "1. Go to the GCP Console -> Monitoring -> Alerting."
echo "2. Find the '$ALERT_NAME' policy and click Edit."
echo "3. Scroll to 'Notifications and name', add your channel, and save."
echo "--------------------------------------------------------"
