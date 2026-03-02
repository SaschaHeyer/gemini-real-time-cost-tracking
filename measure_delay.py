import argparse
import time
import uuid
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.cloud import bigquery

def measure_logging_delay(project_id: str, location: str, dataset_name: str, table_name: str, model_name: str = "gemini-2.5-flash"):
    vertexai.init(project=project_id, location=location)
    
    model = GenerativeModel(model_name)
    
    bq_client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_name}.{table_name}"
    
    # We will use a unique string to easily find the request in BigQuery
    unique_id = str(uuid.uuid4())
    prompt = f"Write a one sentence poem about the word: {unique_id}"
    
    print(f"\nSending request to {model_name}...")
    start_time = time.time()
    
    try:
        response = model.generate_content(prompt)
    except Exception as e:
        print(f"\nError calling Vertex AI: {e}")
        return
        
    request_time = time.time()
    
    print(f"\nRequest completed in {request_time - start_time:.2f} seconds.")
    print("Waiting for log to appear in BigQuery...")
    
    query = f"""
    SELECT 
        logging_time, 
        full_request, 
        full_response,
        JSON_EXTRACT_SCALAR(full_response, '$.usageMetadata.totalTokenCount') as token_count
    FROM `{table_id}`
    WHERE JSON_EXTRACT_SCALAR(full_request, '$.contents[0].parts[0].text') LIKE '%{unique_id}%'
    ORDER BY logging_time DESC
    LIMIT 1
    """
    
    poll_interval = 2.0
    elapsed = 0.0
    max_wait = 300 # Wait up to 5 minutes
    
    while elapsed < max_wait:
        try:
            job = bq_client.query(query)
            results = list(job.result())
            
            if results:
                found_time = time.time()
                delay = found_time - request_time
                print(f"\nSUCCESS: Log found in BigQuery!")
                print(f"Time from request completion to log appearance: {delay:.2f} seconds.")
                print(f"Tokens consumed (from BQ log): {results[0].token_count}")
                return
        except Exception as e:
            # Hide errors like table not found, as it might take time for BQ to create the table
            print(f"Query failed (table might not exist yet)... waiting", end="\r")
            
        print(f"Log not found yet... elapsed: {elapsed:.1f}s", end="\r")
        time.sleep(poll_interval)
        elapsed += poll_interval
        
    print(f"\nTimeout: Log did not appear in BigQuery within {max_wait} seconds.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure delay of Request/Response Logging")
    parser.add_argument("--project_id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="Vertex AI Location")
    parser.add_argument("--dataset_name", default="vertex_ai_logs", help="BigQuery Dataset Name")
    parser.add_argument("--table_name", default="gemini_logs", help="BigQuery Table Name")
    parser.add_argument("--model_name", default="gemini-2.5-flash", help="Model Name")
    
    args = parser.parse_args()
    measure_logging_delay(args.project_id, args.location, args.dataset_name, args.table_name, args.model_name)
