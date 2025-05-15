import os
import time
import datetime
from google.cloud import storage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
LOCAL_OUTPUT_DIRS = ["data", "results", "figures"]

def initialize_storage():
    try:
        logger.info(f"Initializing Google Cloud Storage with bucket: {BUCKET_NAME}")
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        if not bucket.exists():
            logger.warning(f"Bucket {BUCKET_NAME} doesn't exist, attempting to create it")
            bucket = storage_client.create_bucket(BUCKET_NAME)
            logger.info(f"Created new bucket: {BUCKET_NAME}")
        else:
            logger.info(f"Using existing bucket: {BUCKET_NAME}")

        return storage_client, bucket
    except Exception as e:
        logger.error(f"Error initializing cloud storage: {e}", exc_info=True)
        return None, None

def upload_pipeline_outputs(run_id):
    logger.info(f"Starting upload of pipeline outputs for run ID: {run_id}")
    try:
        storage_client, bucket = initialize_storage()
        if not storage_client or not bucket:
            logger.error("Failed to initialize storage. Files will not be uploaded.")
            return {}

        file_urls = {}
        for dir_name in LOCAL_OUTPUT_DIRS:
            if os.path.exists(dir_name):
                logger.info(f"Processing directory: {dir_name}")
                dir_files = os.listdir(dir_name)

                for file_name in dir_files:
                    local_path = os.path.join(dir_name, file_name)
                    if not os.path.isfile(local_path):
                        continue

                    cloud_path = f"{run_id}/{dir_name}/{file_name}"
                    blob = bucket.blob(cloud_path)
                    logger.info(f"Uploading {local_path} to {cloud_path}")

                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            blob.upload_from_filename(local_path)

                            signed_url = blob.generate_signed_url(
                                expiration=datetime.timedelta(hours=24),
                                method="GET"
                            )
                            file_key = f"{dir_name}/{file_name}"
                            file_urls[file_key] = signed_url

                            logger.info(f"Uploaded {file_key} with signed URL")
                            break
                        except Exception as upload_error:
                            if attempt < max_retries - 1:
                                logger.warning(f"Attempt {attempt+1} failed: {upload_error}. Retrying...")
                                time.sleep(2)
                            else:
                                logger.error(f"Upload failed after {max_retries} attempts: {upload_error}")
            else:
                logger.warning(f"Directory not found: {dir_name}")

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
    """Generate a signed URL for accessing a specific file"""
    try:
        storage_client, bucket = initialize_storage()
        if not bucket:
            return None

        cloud_path = f"{run_id}/{local_path}"
        blob = bucket.blob(cloud_path)

        if not blob.exists():
            logger.warning(f"Blob does not exist: {cloud_path}")
            return None

        url = blob.generate_signed_url(
            expiration=datetime.timedelta(hours=24),
            method="GET"
        )
        return url
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
