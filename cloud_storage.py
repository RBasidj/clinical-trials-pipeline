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

## File: cloud_storage.py
## Location: Replace the initialize_storage function completely

def initialize_storage():
    """Initialize and return a Google Cloud Storage client with explicit credentials"""
    try:
        logger.info(f"Initializing Google Cloud Storage with bucket: {BUCKET_NAME}")
        
        # Check for service account credentials file
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        logger.info(f"Looking for credentials at: {credentials_path}")
        
        # Convert relative path to absolute if needed
        if credentials_path and not os.path.isabs(credentials_path):
            abs_path = os.path.abspath(credentials_path)
            logger.info(f"Converting relative path to absolute: {abs_path}")
            credentials_path = abs_path
            # Update environment variable
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
        
        # Try multiple approaches to find credentials
        credentials = None
        project_id = None
        
        # Method 1: Try explicit path from environment variable
        if credentials_path and os.path.exists(credentials_path):
            try:
                from google.oauth2 import service_account
                logger.info(f"Loading credentials from {credentials_path}")
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                project_id = credentials.project_id
                logger.info(f"Loaded credentials for project: {project_id}")
            except Exception as e:
                logger.error(f"Failed to load credentials from {credentials_path}: {e}")

        
        # Method 2: Try servicekey.json in current directory
        if credentials is None:
            try:
                from google.oauth2 import service_account
                local_key = os.path.join(os.getcwd(), 'servicekey.json')
                if os.path.exists(local_key):
                    logger.info(f"Loading credentials from {local_key}")
                    credentials = service_account.Credentials.from_service_account_file(local_key)
                    project_id = credentials.project_id
                    logger.info(f"Loaded credentials for project: {project_id}")
            except Exception as e:
                logger.error(f"Failed to load credentials from local servicekey.json: {e}")
        
        # Initialize storage client
        if credentials and project_id:
            logger.info(f"Creating storage client with explicit credentials for project {project_id}")
            storage_client = storage.Client(project=project_id, credentials=credentials)
        else:
            # Last resort: try default credentials
            logger.warning("Falling back to default credentials (likely to fail in local development)")
            storage_client = storage.Client()
        
        # Check if our bucket exists
        logger.info(f"Checking if bucket {BUCKET_NAME} exists")
        bucket = storage_client.bucket(BUCKET_NAME)
        
        if not bucket.exists():
            logger.warning(f"Bucket {BUCKET_NAME} doesn't exist, attempting to create it")
            try:
                bucket = storage_client.create_bucket(BUCKET_NAME)
                logger.info(f"Created new bucket: {BUCKET_NAME}")
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")
                return None, None
        else:
            logger.info(f"Using existing bucket: {BUCKET_NAME}")
        
        # Check bucket permissions
        try:
            # Try to list blobs to verify access
            list(bucket.list_blobs(max_results=1))
            logger.info("Successfully verified bucket access")
        except Exception as e:
            logger.error(f"Cannot access bucket: {e}")
            logger.error("Service account may not have sufficient permissions")
            return None, None
            
        return storage_client, bucket
    except Exception as e:
        logger.error(f"Error initializing cloud storage: {e}", exc_info=True)
        return None, None


## File: cloud_storage.py
## Location: Replace the upload_pipeline_outputs function completely

## File: cloud_storage.py
## Location: Replace upload_pipeline_outputs function

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

def get_file_url(run_id, local_path):
    """Get the URL for a specific file"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            return None

        cloud_path = f"{run_id}/{local_path}"
        blob = bucket.blob(cloud_path)

        if not blob.exists():
            logger.warning(f"Blob does not exist: {cloud_path}")
            return None

        try:
            # Try to use public URL first
            public_url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
            return public_url
        except Exception as e:
            logger.warning(f"Could not create public URL, using signed URL: {e}")
            # Fall back to signed URL with long expiration if necessary
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(days=7),
                method="GET"
            )
            return signed_url
    except Exception as e:
        logger.error(f"Error getting file URL: {e}", exc_info=True)
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
