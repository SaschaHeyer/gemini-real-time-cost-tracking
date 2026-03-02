import argparse
import vertexai
from vertexai.preview.generative_models import GenerativeModel

def setup_logging(project_id: str, location: str, dataset_name: str, table_name: str, model_name: str = "gemini-2.5-flash"):
    vertexai.init(project=project_id, location=location)
    publisher_model = GenerativeModel(model_name)
    
    bq_dest = f"bq://{project_id}.{dataset_name}.{table_name}"
    
    print(f"Enabling Request/Response logging for {model_name} to {bq_dest}...")
    
    # 1.0 means 100% of requests are logged
    publisher_model.set_request_response_logging_config(
        enabled=True,
        sampling_rate=1.0,
        bigquery_destination=bq_dest
    )
    print("Logging configured successfully!")
    print(f"Any new requests made via the SDK for {model_name} will be logged to BigQuery.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enable Vertex AI GenAI Request/Response Logging")
    parser.add_argument("--project_id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="Vertex AI Location")
    parser.add_argument("--dataset_name", default="vertex_ai_logs", help="BigQuery Dataset Name")
    parser.add_argument("--table_name", default="gemini_logs", help="BigQuery Table Name")
    parser.add_argument("--model_name", default="gemini-2.5-flash", help="Model Name")
    
    args = parser.parse_args()
    setup_logging(args.project_id, args.location, args.dataset_name, args.table_name, args.model_name)
