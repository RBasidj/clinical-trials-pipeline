"""
Google Cloud Run deployment script for Clinical Trials Pipeline
"""
import os
import subprocess
import time
import argparse
import json

# config
PROJECT_ID = "clinicaltrials-v1"
REGION = "us-central1"
SERVICE_NAME = "clinical-trials-pipeline"

def parse_arguments():
    """Parse command line arguments for deployment configuration"""
    parser = argparse.ArgumentParser(description='Deploy Clinical Trials Pipeline to Google Cloud Run')
    
    parser.add_argument('--memory', type=str, default="4Gi",
                        help='Memory allocation (default: 4Gi)')
    
    parser.add_argument('--cpu', type=str, default="2",
                        help='CPU allocation (default: 2)')
    
    parser.add_argument('--timeout', type=str, default="60m",
                        help='Request timeout (default: 60m)')
    
    parser.add_argument('--concurrency', type=int, default=80,
                        help='Maximum number of concurrent requests (default: 80)')
    
    parser.add_argument('--min-instances', type=int, default=0,
                        help='Minimum number of instances (default: 0)')
    
    parser.add_argument('--max-instances', type=int, default=5,
                        help='Maximum number of instances (default: 5)')
    
    return parser.parse_args()

def setup_service_account():
    """Ensure service account exists with proper permissions"""
    print("Setting up service account...")
    
    sa_name = f"clinical-trials-sa@{PROJECT_ID}.iam.gserviceaccount.com"
    sa_exists_cmd = [
        "gcloud", "iam", "service-accounts", "describe", 
        sa_name, "--project", PROJECT_ID
    ]
    
    try:
        #  service account exists
        result = subprocess.run(sa_exists_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Creating service account: {sa_name}")
            create_sa_cmd = [
                "gcloud", "iam", "service-accounts", "create", "clinical-trials-sa",
                "--display-name", "Clinical Trials Pipeline Service Account",
                "--project", PROJECT_ID
            ]
            subprocess.run(create_sa_cmd, check=True)
            print("Service account created successfully.")
            
            # Give the service account time to propagate
            print("Waiting for service account to propagate...")
            time.sleep(5)
        else:
            print(f"Using existing service account: {sa_name}")
        
        roles = [
            "roles/storage.admin",
            "roles/logging.logWriter",
            "roles/cloudsql.client"
        ]
        
        for role in roles:
            print(f"Granting {role} to service account...")
            grant_cmd = [
                "gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
                "--member", f"serviceAccount:{sa_name}",
                "--role", role
            ]
            subprocess.run(grant_cmd, check=True)
        
        return sa_name
    except subprocess.CalledProcessError as e:
        print(f"Error setting up service account: {e}")
        return None

def setup_storage_bucket():
    """Ensure storage bucket exists"""
    bucket_name = f"{PROJECT_ID}-clinical-trials"
    print(f"Setting up storage bucket: {bucket_name}")
    
    check_bucket_cmd = [
        "gsutil", "ls", "-p", PROJECT_ID
    ]
    
    try:
        result = subprocess.run(check_bucket_cmd, capture_output=True, text=True)
        if f"gs://{bucket_name}/" not in result.stdout:
            print(f"Creating storage bucket: {bucket_name}")
            create_bucket_cmd = [
                "gsutil", "mb", "-p", PROJECT_ID, "-l", REGION, f"gs://{bucket_name}/"
            ]
            subprocess.run(create_bucket_cmd, check=True)
            
          
            
            print(f"Storage bucket {bucket_name} created successfully")
        else:
            print(f"Using existing storage bucket: {bucket_name}")
        
        return bucket_name
    except subprocess.CalledProcessError as e:
        print(f"Error setting up storage bucket: {e}")
        return None

def deploy_to_cloud_run(args):
    """Build and deploy to Google Cloud Run with specified resources"""
    print("Building and deploying to Google Cloud Run...")
    
    #  infrastructure
    service_account = setup_service_account()
    bucket_name = setup_storage_bucket()
    
    if not service_account or not bucket_name:
        print("Failed to set up required infrastructure. Aborting deployment.")
        return None
    
    # build container
    build_cmd = [
        "gcloud", "builds", "submit", 
        "--tag", f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}"
    ]
    
    deploy_cmd = [
    "gcloud", "run", "deploy", SERVICE_NAME,
    "--image", f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}",
    "--platform", "managed",
    "--region", REGION,
    "--allow-unauthenticated",
    "--memory", "6Gi",               # Increased from default
    "--cpu", "4",                     # Increased from default
    "--timeout", "30m",             # Increased from default
    "--concurrency", str(args.concurrency),
    "--min-instances", str(args.min_instances),
    "--max-instances", str(args.max_instances),
    "--set-env-vars", f"OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY', '')}",
    "--set-env-vars", f"CLOUD_STORAGE_BUCKET={bucket_name}",
    "--set-env-vars", "DEBUG_CLOUD=1",     # Add debug flag for cloud environment
    "--set-env-vars", "REPORT_GENERATION_TIMEOUT=120",  # Add timeout for report generation
    "--service-account", service_account
]
    
    # Execute 
    try:
        print("Building container...")
        print(f"Running command: {' '.join(build_cmd)}")
        subprocess.run(build_cmd, check=True)
        print("Container built successfully!")
        
        print("Deploying to Cloud Run...")
        print(f"Running command: {' '.join(deploy_cmd)}")
        subprocess.run(deploy_cmd, check=True)
        print(f"Deployed to Cloud Run: {SERVICE_NAME}")
        
        # Get  service URL
        url_cmd = [
            "gcloud", "run", "services", "describe", SERVICE_NAME,
            "--platform", "managed",
            "--region", REGION,
            "--format", "value(status.url)"
        ]
        
        result = subprocess.run(url_cmd, check=True, capture_output=True, text=True)
        service_url = result.stdout.strip()
        
        print(f"Service URL: {service_url}")
        
        deployment_info = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_id": PROJECT_ID,
            "service_name": SERVICE_NAME,
            "region": REGION,
            "url": service_url,
            "resources": {
                "memory": args.memory,
                "cpu": args.cpu,
                "timeout": args.timeout,
                "concurrency": args.concurrency,
                "min_instances": args.min_instances,
                "max_instances": args.max_instances
            },
            "bucket_name": bucket_name,
            "service_account": service_account
        }
        
        with open("deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"Deployment info saved to deployment_info.json")
        
        return service_url
        
    except subprocess.CalledProcessError as e:
        print(f"Deployment failed: {e}")
        return None

if __name__ == "__main__":
    args = parse_arguments()
    print(f"Deploying with: Memory={args.memory}, CPU={args.cpu}, Timeout={args.timeout}")
    deploy_to_cloud_run(args)