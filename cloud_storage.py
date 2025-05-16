import os
import time
import datetime
from google.cloud import storage
import logging
from dotenv import load_dotenv
load_dotenv()  #  environment variables from .env file


logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
LOCAL_OUTPUT_DIRS = ["data", "results", "figures"]

# my new key file: IF YOU ARE TRYING TO IMPLEMENT NON-LOCALLY YOU NEED A KEY!

def initialize_storage():
    """Initialize Google Cloud Storage client with better error handling and logging"""
    try:
        logger.info(f"Initializing Google Cloud Storage with bucket: {BUCKET_NAME}")
        
        #  key file to the list of possible credential locations
        cred_locations = [
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
            "clinicaltrials-v1-5c24014c74c9.json",  # Your new key file
            os.path.join(os.getcwd(), "clinicaltrials-v1-5c24014c74c9.json"),
            "servicekey.json",
            "clinicaltrials-v1-9acf57d456a4.json",  # Keep old key as fallback
            os.path.join(os.path.expanduser("~"), ".config/gcp", "clinicaltrials-v1-5c24014c74c9.json"),
            "/app/clinicaltrials-v1-5c24014c74c9.json"  # For Cloud Run
        ]
        
        creds_path = None
        for loc in cred_locations:
            if loc and os.path.exists(loc):
                creds_path = loc
                logger.info(f"Found credentials at: {creds_path}")
                break
        
        if creds_path:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            project_id = credentials.project_id
            logger.info(f"Loaded credentials for project: {project_id}")
            storage_client = storage.Client(credentials=credentials, project=project_id)
        else:
            logger.warning("No explicit credentials found, using default credentials")
            #  use the new environment variable directly if file not found
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "clinicaltrials-v1-5c24014c74c9.json"
            try:
                storage_client = storage.Client()
            except Exception as client_error:
                logger.error(f"Failed to create storage client: {client_error}")
                return None, None
        
        logger.info(f"Checking if bucket {BUCKET_NAME} exists")
        bucket = storage_client.bucket(BUCKET_NAME)
        
        if not bucket.exists():
            logger.warning(f"Bucket {BUCKET_NAME} doesn't exist, attempting to create it")
            bucket = storage_client.create_bucket(BUCKET_NAME)
            logger.info(f"Created new bucket: {BUCKET_NAME}")
            
            bucket.make_public(future=True)
            logger.info(f"Made bucket {BUCKET_NAME} publicly readable")
        else:
            logger.info(f"Using existing bucket: {BUCKET_NAME}")
            
        try:
            blobs = list(bucket.list_blobs(max_results=1))
            logger.info("Successfully verified bucket access")
        except Exception as e:
            logger.warning(f"Permission verification warning: {e}")
        
        return storage_client, bucket
    except Exception as e:
        logger.error(f"Error initializing cloud storage: {e}", exc_info=True)
        return None, None

#debugging cloud storage
def check_result_exists(run_id, filename):
    """Check if a specific file exists for the run in cloud storage"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            return False
            
        blob_path = f"{run_id}/results/{filename}"
        blob = bucket.blob(blob_path)
        
        exists = blob.exists()
        logger.info(f"File check: {blob_path} exists: {exists}")
        return exists
    except Exception as e:
        logger.error(f"Error checking if file exists: {e}")
        return False

def add_empty_report(run_id):
    """Create an empty report file if one doesn't exist (for debugging purposes)"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error("Failed to initialize storage for creating empty report")
            return False
        
        #  report already exists ?
        report_path = f"{run_id}/results/report.md"
        blob = bucket.blob(report_path)
        
        if not blob.exists():
            logger.warning(f"Report doesn't exist, creating empty placeholder: {report_path}")
            
            #  empty report
            empty_report = "# Analysis Report (Placeholder)\n\nThis is an automatically generated placeholder report."
            
            # Upload the empty report
            blob.upload_from_string(empty_report)
            
            #  a signed URL
            signed_url = blob.generate_signed_url(
                expiration=datetime.timedelta(hours=24),
                method="GET"
            )
            
            logger.info(f"Created placeholder report at: {signed_url}")
            return True
        else:
            logger.info(f"Report already exists: {report_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating empty report: {e}")
        return False

#this kind of function scales especially well between multiple GCP instances:
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
        
        # upload files
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

                    for attempt in range(3):
                        try:
                            blob.upload_from_filename(local_path)
                            
                            try:
                                policy = bucket.get_iam_policy(requested_policy_version=3)
                                policy.bindings.append({
                                    "role": "roles/storage.objectViewer",
                                    "members": ["allUsers"],
                                })
                                bucket.set_iam_policy(policy)
                                public_url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
                                file_key = f"{dir_name}/{file_name}"
                                file_urls[file_key] = public_url
                            except Exception as e:
                                logger.warning(f"Could not make bucket public, using signed URL: {e}")
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


def get_file_url(run_id, local_path):
    """Generate a signed URL for accessing a specific file with better error handling"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error(f"Failed to initialize storage bucket for {run_id}/{local_path}")
            return None

        #  various path formats
        path_formats = [
            f"{run_id}/{local_path}",          #  path
            f"{run_id}/{local_path.lstrip('/')}", #  leading slash if present
            local_path,                        # Direct path without run_id
            f"{run_id}/{os.path.basename(local_path)}"  
        ]
        
        #  each path format
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

        # file not found? uh oh!
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
