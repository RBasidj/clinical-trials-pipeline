"""
Simple script to test Google Cloud Storage access.
"""
import os
from google.cloud import storage
import json

def test_cloud_storage():
    """Test Google Cloud Storage connection and operations"""
    # Print environment variables (redacted for security)
    print("Checking environment variables...")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        print(f"GOOGLE_APPLICATION_CREDENTIALS is set to: {credentials_path}")
        if os.path.exists(credentials_path):
            print(f"Credentials file exists")
        else:
            print(f"WARNING: Credentials file does not exist at {credentials_path}")
    else:
        print("WARNING: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
    
    bucket_name = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
    print(f"Using bucket name: {bucket_name}")
    
    # Test file to upload
    test_file_path = "test_cloud_storage.txt"
    with open(test_file_path, "w") as f:
        f.write(f"Test file created at {os.path.abspath(test_file_path)}")
    
    try:
        # Initialize storage client
        print("Initializing storage client...")
        storage_client = storage.Client()
        
        print("Checking available buckets...")
        buckets = list(storage_client.list_buckets())
        print(f"Found {len(buckets)} buckets:")
        for bucket in buckets:
            print(f"  - {bucket.name}")
        
        # Get bucket
        print(f"Getting bucket: {bucket_name}")
        bucket = storage_client.bucket(bucket_name)
        
        if not bucket.exists():
            print(f"Bucket {bucket_name} does not exist. Attempting to create it...")
            bucket = storage_client.create_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
        
        # Upload test file
        print(f"Uploading test file: {test_file_path}")
        blob = bucket.blob("test_upload.txt")
        blob.upload_from_filename(test_file_path)
        
        # Make it public
        blob.make_public()
        
        print(f"Uploaded file successfully.")
        print(f"File is available at: {blob.public_url}")
        
        # Upload a test image
        print("Creating and uploading a test image...")
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Create a simple test plot
            plt.figure(figsize=(8, 6))
            x = np.linspace(0, 10, 100)
            y = np.sin(x)
            plt.plot(x, y)
            plt.title('Test Plot')
            plt.xlabel('X')
            plt.ylabel('sin(X)')
            plt.grid(True)
            
            # Save to file
            test_image = "test_image.png"
            plt.savefig(test_image)
            plt.close()
            
            # Upload image
            image_blob = bucket.blob("test_image.png")
            image_blob.upload_from_filename(test_image)
            image_blob.make_public()
            
            print(f"Uploaded test image successfully.")
            print(f"Image is available at: {image_blob.public_url}")
            
        except Exception as e:
            print(f"Error creating/uploading test image: {e}")
        
        return True
    except Exception as e:
        print(f"Error testing cloud storage: {e}")
        return False

if __name__ == "__main__":
    success = test_cloud_storage()
    if success:
        print("\nCloud storage test completed successfully!")
    else:
        print("\nCloud storage test failed!")