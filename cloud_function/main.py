import functions_framework
import os
from google.cloud import bigquery

@functions_framework.http
def check_vertex_usage(request):
    """HTTP Cloud Function that polls BigQuery for Vertex AI usage and logs alerts if a threshold is exceeded."""
    project_id = os.environ.get("PROJECT_ID")
    dataset_name = os.environ.get("DATASET_NAME", "vertex_ai_logs")
    table_name = os.environ.get("TABLE_NAME", "gemini_logs")
    window_minutes = int(os.environ.get("WINDOW_MINUTES", 10))
    threshold = int(os.environ.get("TOKEN_THRESHOLD", 5000))

    if not project_id:
        return "PROJECT_ID environment variable not set.", 500

    bq_client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    
    query = f"""
    WITH TokenUsage AS (
      SELECT
        logging_time as timestamp,
        model,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.totalTokenCount') AS INT64) AS token_count,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.promptTokenCount') AS INT64) AS prompt_tokens,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64) AS candidate_tokens
      FROM
        `{table_id}`
      WHERE
        logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {window_minutes} MINUTE)
    )
    SELECT
      model,
      COUNT(*) as request_count,
      SUM(token_count) as total_tokens
    FROM
      TokenUsage
    GROUP BY
      model
    """
    
    print(f"Checking usage in {table_id} for the last {window_minutes} minutes...")
    
    try:
        job = bq_client.query(query)
        results = list(job.result())
        
        alerts_triggered = 0
        for row in results:
            print(f"Model: {row.model} | Requests: {row.request_count} | Total Tokens: {row.total_tokens}")
            
            # Check against threshold
            if row.total_tokens and row.total_tokens > threshold:
                msg = f"🚨 HIGH VERTEX AI USAGE ALERT: Model '{row.model}' consumed {row.total_tokens} tokens in the last {window_minutes} minutes (Threshold: {threshold})."
                # In a real-world scenario, you would route this via Pub/Sub, Email, PagerDuty, or Slack.
                # For now, we print to Cloud Logging which can trigger Log-based alerts.
                print(msg)
                alerts_triggered += 1
                
        return f"Processed {len(results)} model records. Alerts generated: {alerts_triggered}", 200
            
    except Exception as e:
        error_msg = f"Error querying BigQuery: {e}"
        print(error_msg)
        return error_msg, 500
