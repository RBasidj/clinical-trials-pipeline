"""
Google Cloud Run deployment script for Clinical Trials Pipeline
"""
import os
import subprocess
import time

# Configuration
PROJECT_ID= "clinicaltrials-v1"
REGION = "us-central1"
SERVICE_NAME = "clinical-trials-pipeline"

# Build and deploy
def deploy_to_cloud_run():
    print("Building and deploying to Google Cloud Run...")
    
    # Build the container
    build_cmd = [
        "gcloud", "builds", "submit", 
        "--tag", f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}"
    ]
    
    # Deploy to Cloud Run
    deploy_cmd = [
        "gcloud", "run", "deploy", SERVICE_NAME,
        "--image", f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}",
        "--platform", "managed",
        "--region", REGION,
        "--allow-unauthenticated",
        "--memory", "2Gi",
        "--timeout", "30m",
        "--set-env-vars", f"OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY', '')}",
        "--set-env-vars", f"CLOUD_STORAGE_BUCKET={PROJECT_ID}-clinical-trials",
        "--service-account", f"clinical-trials-sa@{PROJECT_ID}.iam.gserviceaccount.com"
    ]
    
    # Execute commands
    try:
        subprocess.run(build_cmd, check=True)
        print("Container built successfully!")
        
        subprocess.run(deploy_cmd, check=True)
        print(f"Deployed to Cloud Run: {SERVICE_NAME}")
        
        # Get the service URL
        url_cmd = [
            "gcloud", "run", "services", "describe", SERVICE_NAME,
            "--platform", "managed",
            "--region", REGION,
            "--format", "value(status.url)"
        ]
        
        result = subprocess.run(url_cmd, check=True, capture_output=True, text=True)
        service_url = result.stdout.strip()
        
        print(f"Service URL: {service_url}")
        return service_url
        
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")
        return None
# Add this to your deploy_cloud.py script
deploy_cmd = [
    "gcloud", "run", "deploy", SERVICE_NAME,
    "--image", f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}",
    "--platform", "managed",
    "--region", REGION,
    "--allow-unauthenticated",
    "--memory", "2Gi",
    "--timeout", "30m",
    "--set-env-vars", f"OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY', '')}",
    "--set-env-vars", f"CLOUD_STORAGE_BUCKET={PROJECT_ID}-clinical-trials",
    "--service-account", "clinical-trials-sa@${PROJECT_ID}.iam.gserviceaccount.com"
]
if __name__ == "__main__":
    deploy_to_cloud_run()