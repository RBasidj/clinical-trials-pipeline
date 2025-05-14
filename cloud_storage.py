"""
Google Cloud Storage integration for the clinical trials pipeline.
Handles file storage and retrieval for pipeline outputs.
"""
import os
from google.cloud import storage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Google Cloud Storage
BUCKET_NAME = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
LOCAL_OUTPUT_DIRS = ["data", "results", "figures"]

def initialize_storage():
    """Initialize and return a Google Cloud Storage client"""
    try:
        logger.info(f"Initializing Google Cloud Storage with bucket: {BUCKET_NAME}")
        storage_client = storage.Client()
        
        # Check if our bucket exists
        bucket = storage_client.bucket(BUCKET_NAME)
        if not bucket.exists():
            logger.warning(f"Bucket {BUCKET_NAME} doesn't exist, attempting to create it")
            bucket = storage_client.create_bucket(BUCKET_NAME)
            logger.info(f"Created new bucket: {BUCKET_NAME}")
        else:
            logger.info(f"Using existing bucket: {BUCKET_NAME}")
            
        return storage_client, bucket
    except Exception as e:
        logger.error(f"Error initializing cloud storage: {e}")
        return None, None

def upload_pipeline_outputs(run_id):
    """Upload all pipeline outputs to cloud storage with a specific run ID"""
    logger.info(f"Starting upload of pipeline outputs for run ID: {run_id}")
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error("Failed to initialize storage. Files will not be uploaded.")
            return {}
        
        file_urls = {}
        file_count = 0
        
        # Upload all files from the output directories
        for dir_name in LOCAL_OUTPUT_DIRS:
            if os.path.exists(dir_name):
                logger.info(f"Processing directory: {dir_name}")
                for file_name in os.listdir(dir_name):
                    local_path = os.path.join(dir_name, file_name)
                    if os.path.isfile(local_path):
                        # Create cloud path with run_id to organize files
                        cloud_path = f"{run_id}/{dir_name}/{file_name}"
                        
                        # Upload file
                        blob = bucket.blob(cloud_path)
                        logger.info(f"Uploading {local_path} to {cloud_path}")
                        blob.upload_from_filename(local_path)
                        
                        # Make the file publicly accessible
                        blob.make_public()
                        
                        # Store the public URL
                        file_urls[local_path] = blob.public_url
                        file_count += 1
                        
                        logger.info(f"Uploaded {local_path} to {cloud_path}")
            else:
                logger.warning(f"Directory not found: {dir_name}")
        
        logger.info(f"Completed uploading {file_count} files for run ID: {run_id}")
        return file_urls
    except Exception as e:
        logger.error(f"Error uploading files to cloud storage: {e}")
        return {}

def download_pipeline_outputs(run_id, local_dir="downloads"):
    """Download all files for a specific run ID from cloud storage"""
    logger.info(f"Starting download of pipeline outputs for run ID: {run_id}")
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            logger.error("Failed to initialize storage. Files will not be downloaded.")
            return []
        
        # Create the download directory if it doesn't exist
        os.makedirs(local_dir, exist_ok=True)
        
        downloaded_files = []
        
        # List all objects with the run_id prefix
        blobs = list(bucket.list_blobs(prefix=f"{run_id}/"))
        logger.info(f"Found {len(blobs)} files to download for run ID: {run_id}")
        
        for blob in blobs:
            # Skip directory markers
            if blob.name.endswith('/'):
                continue
                
            # Extract the relative path after the run_id
            rel_path = blob.name.split('/', 1)[1] if '/' in blob.name else blob.name
            local_path = os.path.join(local_dir, rel_path)
            
            # Create parent directories if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download the file
            logger.info(f"Downloading {blob.name} to {local_path}")
            blob.download_to_filename(local_path)
            downloaded_files.append(local_path)
        
        logger.info(f"Completed downloading {len(downloaded_files)} files")
        return downloaded_files
    except Exception as e:
        logger.error(f"Error downloading files from cloud storage: {e}")
        return []

def get_file_url(run_id, local_path):
    """Get the public URL for a specific file"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            return None
            
        # Extract directory and filename
        cloud_path = f"{run_id}/{local_path}"
        
        # Get the blob
        blob = bucket.blob(cloud_path)
        
        # Make sure it's public
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        logger.error(f"Error getting file URL: {e}")
        return None