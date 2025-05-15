import os
import time
import datetime
from google.cloud import storage
import logging
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file


# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
LOCAL_OUTPUT_DIRS = ["data", "results", "figures"]

def initialize_storage():
    """Initialize Google Cloud Storage client with better error handling and logging"""
    try:
        logger.info(f"Initializing Google Cloud Storage with bucket: {BUCKET_NAME}")
        
        # Look for credentials file in various locations
        cred_locations = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "clinicaltrials-v1-9acf57d456a4.json",  # Current directory
            os.path.join(os.path.expanduser("~"), ".config/gcp", "clinicaltrials-v1-9acf57d456a4.json"),
            "/app/clinicaltrials-v1-9acf57d456a4.json"  # For Cloud Run
        ]
        
        # Try to find and load credentials
        creds_path = None
        for loc in cred_locations:
            if loc and os.path.exists(loc):
                creds_path = loc
                logger.info(f"Looking for credentials at: {creds_path}")
                logger.info(f"Loading credentials from {creds_path}")
                break
        
        if creds_path:
            # Use explicit credentials
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            project_id = credentials.project_id
            logger.info(f"Loaded credentials for project: {project_id}")
            logger.info(f"Creating storage client with explicit credentials for project {project_id}")
            storage_client = storage.Client(credentials=credentials, project=project_id)
        else:
            # Fall back to default credentials
            logger.info("No explicit credentials found, using default credentials")
            storage_client = storage.Client()
        
        logger.info(f"Checking if bucket {BUCKET_NAME} exists")
        bucket = storage_client.bucket(BUCKET_NAME)
        
        if not bucket.exists():
            logger.warning(f"Bucket {BUCKET_NAME} doesn't exist, attempting to create it")
            bucket = storage_client.create_bucket(BUCKET_NAME)
            logger.info(f"Created new bucket: {BUCKET_NAME}")
            
            # Make bucket public (optional)
            bucket.make_public(future=True)
            logger.info(f"Made bucket {BUCKET_NAME} publicly readable")
        else:
            logger.info(f"Using existing bucket: {BUCKET_NAME}")
            
        # Verify permissions by doing a simple operation
        try:
            blobs = list(bucket.list_blobs(max_results=1))
            logger.info("Successfully verified bucket access")
        except Exception as e:
            logger.warning(f"Permission verification warning: {e}")
        
        return storage_client, bucket
    except Exception as e:
        logger.error(f"Error initializing cloud storage: {e}", exc_info=True)
        return None, None


def upload_pipeline_outputs(run_id):
    """Upload all pipeline outputs to cloud storage with a specific run ID"""
    logger.info(f"Starting upload of pipeline outputs for run ID: {run_id}")
    try:
        storage_client, bucket = initialize_storage()
        if not storage_client or not bucket:
            logger.error("Failed to initialize storage. Files will not be uploaded.")
            return {}
        
        file_urls = {}
        file_count = 0
        
        # Upload all files from the output directories
        for dir_name in LOCAL_OUTPUT_DIRS:
            if os.path.exists(dir_name):
                logger.info(f"Processing directory: {dir_name}")
                dir_files = os.listdir(dir_name)
                logger.info(f"Found {len(dir_files)} files in {dir_name}")
                
                for file_name in dir_files:
                    local_path = os.path.join(dir_name, file_name)
                    if not os.path.isfile(local_path):
                        continue

                    cloud_path = f"{run_id}/{dir_name}/{file_name}"
                    blob = bucket.blob(cloud_path)
                    logger.info(f"Uploading {local_path} to {cloud_path}")

                    # Upload with retry logic
                    for attempt in range(3):
                        try:
                            blob.upload_from_filename(local_path)
                            
                            # Instead of make_public(), use IAM policy to make publicly accessible
                            # or generate a signed URL with longer expiration
                            try:
                                # Try to make public without ACLs (for uniform bucket-level access)
                                policy = bucket.get_iam_policy(requested_policy_version=3)
                                policy.bindings.append({
                                    "role": "roles/storage.objectViewer",
                                    "members": ["allUsers"],
                                })
                                bucket.set_iam_policy(policy)
                                # Use public URL
                                public_url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
                                file_key = f"{dir_name}/{file_name}"
                                file_urls[file_key] = public_url
                            except Exception as e:
                                # Fall back to signed URL with long expiration if public access fails
                                logger.warning(f"Could not make bucket public, using signed URL: {e}")
                                # Create a signed URL that's valid for 7 days
                                signed_url = blob.generate_signed_url(
                                    version="v4",
                                    expiration=datetime.timedelta(days=7),
                                    method="GET"
                                )
                                file_key = f"{dir_name}/{file_name}"
                                file_urls[file_key] = signed_url
                            
                            file_count += 1
                            logger.info(f"Successfully uploaded and shared {file_key}")
                            break
                        except Exception as upload_error:
                            if attempt < 2:
                                logger.warning(f"Attempt {attempt+1} failed: {upload_error}. Retrying...")
                                time.sleep(2)
                            else:
                                logger.error(f"Upload failed after 3 attempts: {upload_error}")
            else:
                logger.warning(f"Directory not found: {dir_name}")
        
        logger.info(f"Completed uploading {file_count} files for run ID: {run_id}")
        return file_urls
    except Exception as e:
        logger.error(f"Error uploading files to cloud storage: {e}", exc_info=True)
        return {}


def download_pipeline_outputs(run_id, local_dir="downloads"):
    logger.info(f"Starting download of pipeline outputs for run ID: {run_id}")
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error("Failed to initialize storage.")
            return []

        os.makedirs(local_dir, exist_ok=True)
        downloaded_files = []

        blobs = list(bucket.list_blobs(prefix=f"{run_id}/"))
        for blob in blobs:
            if blob.name.endswith('/'):
                continue

            rel_path = blob.name.split('/', 1)[1] if '/' in blob.name else blob.name
            local_path = os.path.join(local_dir, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            for attempt in range(3):
                try:
                    blob.download_to_filename(local_path)
                    downloaded_files.append(local_path)
                    break
                except Exception as download_error:
                    if attempt < 2:
                        logger.warning(f"Download retry {attempt+1}: {download_error}")
                        time.sleep(2)
                    else:
                        logger.error(f"Failed to download {blob.name}: {download_error}")
        return downloaded_files
    except Exception as e:
        logger.error(f"Error downloading files: {e}")
        return []

## File: cloud_storage.py
## Location: Replace the get_file_url function completely

## File: cloud_storage.py
## Location: Replace get_file_url function

## File: cloud_storage.py
## Location: Update the get_file_url function

## File: cloud_storage.py
## Location: Update the get_file_url function

def get_file_url(run_id, local_path):
    """Generate a signed URL for accessing a specific file with better error handling"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error(f"Failed to initialize storage bucket for {run_id}/{local_path}")
            return None

        # Try various path formats
        path_formats = [
            f"{run_id}/{local_path}",          # Standard path
            f"{run_id}/{local_path.lstrip('/')}", # Remove leading slash if present
            local_path,                        # Direct path without run_id
            f"{run_id}/{os.path.basename(local_path)}"  # Just the filename with run_id
        ]
        
        # Try each path format
        for cloud_path in path_formats:
            logger.info(f"Trying path: {cloud_path}")
            blob = bucket.blob(cloud_path)
            
            if blob.exists():
                logger.info(f"Found blob at path: {cloud_path}")
                try:
                    url = blob.generate_signed_url(
                        expiration=datetime.timedelta(days=7),
                        method="GET"
                    )
                    logger.info(f"Generated signed URL for {cloud_path} valid for 7 days")
                    return url
                except Exception as url_error:
                    logger.warning(f"Could not generate signed URL: {url_error}")
                    
                    # Try public URL as fallback
                    try:
                        blob.make_public()
                        logger.info(f"Made blob {cloud_path} public")
                        return blob.public_url
                    except Exception as public_error:
                        logger.warning(f"Could not make blob public: {public_error}")
                        pass

        # If we reach here, the file wasn't found in any of the tried paths
        logger.error(f"File not found in cloud storage: tried {path_formats}")
        return None
    except Exception as e:
        logger.error(f"Error getting file URL for {run_id}/{local_path}: {e}", exc_info=True)
        return None

def list_run_files(run_id):
    """List all files for a specific run ID with signed URLs"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            return []

        blobs = list(bucket.list_blobs(prefix=f"{run_id}/"))
        files = []

        for blob in blobs:
            if blob.name.endswith('/'):
                continue

            rel_path = blob.name.split('/', 1)[1] if '/' in blob.name else blob.name

            signed_url = blob.generate_signed_url(
                expiration=datetime.timedelta(hours=24),
                method="GET"
            )

            files.append({
                'path': rel_path,
                'size': blob.size,
                'updated': blob.updated,
                'url': signed_url
            })

        return files
    except Exception as e:
        logger.error(f"Error listing run files: {e}", exc_info=True)
        return []
