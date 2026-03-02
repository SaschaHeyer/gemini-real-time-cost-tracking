import argparse
from google.cloud import bigquery

def check_recent_usage(project_id: str, dataset_name: str, table_name: str, window_minutes: int):
    bq_client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    
    query = f"""
    WITH TokenUsage AS (
      SELECT
        logging_time as timestamp,
        model,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.totalTokenCount') AS INT64) AS token_count,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.promptTokenCount') AS INT64) AS prompt_tokens,
        CAST(JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.candidatesTokenCount') AS INT64) AS candidate_tokens,
        JSON_EXTRACT_SCALAR(full_request, '$.contents[0].parts[0].text') AS prompt_preview
      FROM
        `{table_id}`
      WHERE
        logging_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {window_minutes} MINUTE)
    )
    SELECT
      model,
      COUNT(*) as request_count,
      SUM(prompt_tokens) as total_prompt_tokens,
      SUM(candidate_tokens) as total_candidate_tokens,
      MAX(token_count) as max_tokens_single_request
    FROM
      TokenUsage
    GROUP BY
      model
    """
    
    print(f"Checking usage in {table_id} for the last {window_minutes} minutes...")
    try:
        job = bq_client.query(query)
        results = list(job.result())
        
        if not results:
            print("No requests found in the given window.")
            return
            
        for row in results:
            print(f"Model: {row.model}")
            print(f"  Requests: {row.request_count}")
            print(f"  Prompt Tokens: {row.total_prompt_tokens}")
            print(f"  Candidate Tokens: {row.total_candidate_tokens}")
            print(f"  Max Tokens in Single Request: {row.max_tokens_single_request}")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error querying BigQuery: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check token consumption in a rolling window")
    parser.add_argument("--project_id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--dataset_name", default="vertex_ai_logs", help="BigQuery Dataset Name")
    parser.add_argument("--table_name", default="gemini_logs", help="BigQuery Table Name")
    parser.add_argument("--window_minutes", type=int, default=10, help="Rolling window size in minutes")
    
    args = parser.parse_args()
    check_recent_usage(args.project_id, args.dataset_name, args.table_name, args.window_minutes)
