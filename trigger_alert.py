import argparse
import time
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import os

def trigger_alert(project_id: str, location: str, model_name: str = "gemini-2.5-flash", target_tokens: int = 5500):
    """
    Sends multiple requests to Vertex AI until the estimated total tokens exceed the threshold.
    """
    print(f"Initializing Vertex AI in {project_id}...")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    
    # A prompt designed to generate a moderately long response (~500-1000 tokens)
    # We ask for a short story, which typically yields a consistent chunk of tokens.
    prompt = """
    Write a detailed, 500-word short story about a brave database administrator 
    who must journey into the depths of a legacy mainframe to defeat a rogue 
    Artificial Intelligence that has been consuming all the company's compute credits.
    Include vivid descriptions of the server room, the terminal interfaces, and the 
    final confrontation.
    """
    
    print(f"\nGoal: Generate > {target_tokens} tokens to trigger an alert.")
    print("Sending requests...\n")
    
    total_tokens_consumed = 0
    request_count = 0
    
    while total_tokens_consumed < target_tokens:
        request_count += 1
        print(f"Request #{request_count} in progress...")
        
        try:
            start_time = time.time()
            response = model.generate_content(prompt)
            latency = time.time() - start_time
            
            # Extract token count from the response metadata
            usage = response.usage_metadata
            tokens_this_request = usage.total_token_count
            total_tokens_consumed += tokens_this_request
            
            print(f"  -> Success! Generated {tokens_this_request} tokens in {latency:.2f}s.")
            print(f"  -> Total tokens so far: {total_tokens_consumed} / {target_tokens}")
            
        except Exception as e:
            print(f"  -> Error: {e}")
            print("  -> Waiting 5 seconds before retrying...")
            time.sleep(5)
            
        time.sleep(1) # Small pause to avoid rate limits
        
    print(f"\nDone! Triggered {request_count} requests for a total of {total_tokens_consumed} tokens.")
    print("\nNext steps to verify the alert:")
    print("1. Wait ~2 seconds for the logs to stream to BigQuery.")
    print("2. The Cloud Scheduler job will run within the next 10 minutes.")
    print("3. Alternatively, manually trigger the Cloud Function now to see the alert immediately:")
    print("   gcloud scheduler jobs run vertex-ai-log-monitor-job --location=us-central1")
    print("4. Check your Google Cloud Logging for the '🚨 HIGH VERTEX AI USAGE ALERT' message.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger a token threshold alert")
    parser.add_argument("--project_id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="Vertex AI Location")
    parser.add_argument("--model_name", default="gemini-2.5-flash", help="Model Name")
    parser.add_argument("--target_tokens", type=int, default=5500, help="Target total tokens to generate")
    
    args = parser.parse_args()
    trigger_alert(args.project_id, args.location, args.model_name, args.target_tokens)
