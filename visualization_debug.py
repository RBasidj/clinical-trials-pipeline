#!/usr/bin/env python
"""
Test script to debug visualization generation issues.
"""
import os
import sys
import json
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import logging

from dotenv import load_dotenv
load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('visualization_test.log')
    ]
)
logger = logging.getLogger("visualization-test")

def test_matplotlib_backend():
    """Test if matplotlib can generate plots with current backend"""
    logger.info("Testing matplotlib backend...")

    # Print available backends
    logger.info(f"Available matplotlib backends: {matplotlib.rcsetup.all_backends}")

    # Get current backend
    current_backend = matplotlib.get_backend()
    logger.info(f"Current matplotlib backend: {current_backend}")

    try:
        # Create a simple test plot
        plt.figure(figsize=(8, 6))
        plt.plot([1, 2, 3, 4], [10, 20, 25, 30])
        plt.title('Test Plot')
        plt.xlabel('X-axis')
        plt.ylabel('Y-axis')

        # Save the plot
        test_output = 'test_plot.png'
        plt.savefig(test_output)
        plt.close()

        # Check if file was created
        if os.path.exists(test_output):
            file_size = os.path.getsize(test_output)
            logger.info(f"✅ Successfully created test plot ({file_size} bytes): {test_output}")
            return True
        else:
            logger.error(f"❌ Failed to create test plot: {test_output}")
            return False

    except Exception as e:
        logger.error(f"❌ Error generating test plot: {e}", exc_info=True)
        return False

def test_visualization_module():
    """Test the visualization module with sample data"""
    logger.info("Testing visualization module...")

    try:
        sys.path.append('.')
        from visualization import create_visualizations

        test_trials = [
            {'nct_id': 'NCT001', 'start_date': '2020-01-01', 'enrollment': '100', 'sponsor': 'Test Sponsor', 'duration_days': '365', 'interventions': [{'name': 'Drug A'}]},
            {'nct_id': 'NCT002', 'start_date': '2021-02-15', 'enrollment': '250', 'sponsor': 'Another Sponsor', 'duration_days': '180', 'interventions': [{'name': 'Drug B'}]},
            {'nct_id': 'NCT003', 'start_date': '2022-06-30', 'enrollment': '500', 'sponsor': 'Test Sponsor', 'duration_days': '730', 'interventions': [{'name': 'Drug C'}]},
        ]

        test_interventions = [
            {'name': 'Drug A', 'modality': 'small molecule', 'target': 'enzyme X'},
            {'name': 'Drug B', 'modality': 'monoclonal antibody', 'target': 'receptor Y'},
            {'name': 'Drug C', 'modality': 'gene therapy', 'target': 'gene Z'}
        ]

        test_dir = 'test_figures'
        os.makedirs(test_dir, exist_ok=True)

        logger.info(f"Calling create_visualizations with test data to {test_dir}")
        visualization_files = create_visualizations(test_trials, test_interventions, output_dir=test_dir)

        if visualization_files:
            logger.info(f"✅ Successfully created {len(visualization_files)} visualization files")
            for file in visualization_files:
                file_size = os.path.getsize(file)
                logger.info(f"  - {file} ({file_size} bytes)")
            return True
        else:
            logger.error("❌ No visualization files were created")
            return False

    except Exception as e:
        logger.error(f"❌ Error testing visualization module: {e}", exc_info=True)
        return False

## File: visualization_debug.py
## Location: Modify the test_cloud_storage function

def test_cloud_storage():
    """Test cloud storage upload and retrieval"""
    logger.info("Testing cloud storage...")

    try:
        sys.path.append('.')
        from cloud_storage import initialize_storage, upload_pipeline_outputs, get_file_url

        # Create test directory and file
        test_run_id = "debug_run"
        test_dir = 'test_figures'
        os.makedirs(test_dir, exist_ok=True)

        # Create a test file
        test_file_path = os.path.join(test_dir, 'test_image.png')
        plt.figure(figsize=(4, 3))
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.title("Test Cloud Storage")
        plt.savefig(test_file_path)
        plt.close()

        # Make our test image available to cloud_storage module
        if not os.path.exists('figures'):
            os.makedirs('figures', exist_ok=True)
        figures_test_path = os.path.join('figures', 'test_cloud_storage.png')
        plt.figure(figsize=(4, 3))
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.title("Test Cloud Storage")
        plt.savefig(figures_test_path)
        plt.close()

        # Test storage client directly
        from google.cloud import storage
        from google.oauth2 import service_account
        
        # Look for service account key
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "servicekey.json")
        if not os.path.exists(credentials_path):
            # Check in current directory
            cwd_path = os.path.join(os.getcwd(), 'servicekey.json')
            if os.path.exists(cwd_path):
                credentials_path = cwd_path
                logger.info(f"Found credentials at: {credentials_path}")
        
        if os.path.exists(credentials_path):
            logger.info(f"Testing direct authentication with: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            project_id = credentials.project_id
            logger.info(f"Project ID from credentials: {project_id}")
            
            # Try direct bucket access
            try:
                bucket_name = os.environ.get("CLOUD_STORAGE_BUCKET", "clinicaltrialsv1")
                storage_client = storage.Client(credentials=credentials, project=project_id)
                bucket = storage_client.bucket(bucket_name)
                
                if not bucket.exists():
                    logger.info(f"Creating bucket: {bucket_name}")
                    bucket = storage_client.create_bucket(bucket_name)
                
                # Upload test file directly
                blob = bucket.blob("test_direct_upload.txt")
                with open("test_direct_upload.txt", "w") as f:
                    f.write("This is a test upload")
                    
                blob.upload_from_filename("test_direct_upload.txt")
                logger.info("Direct upload successful")
            except Exception as bucket_e:
                logger.error(f"Direct bucket test failed: {bucket_e}")
        
        # Now try the regular upload function
        logger.info(f"Testing upload_pipeline_outputs for run_id: {test_run_id}")
        file_urls = upload_pipeline_outputs(run_id=test_run_id)

        if file_urls:
            logger.info(f"✅ Uploaded {len(file_urls)} files to Cloud Storage:")
            for path, url in file_urls.items():
                logger.info(f"  - {path}: {url}")
                # Test retrieval
                test_url = get_file_url(run_id=test_run_id, local_path=path)
                logger.info(f"  - Retrieved URL: {test_url}")
            return True
        else:
            logger.error("❌ No files were uploaded to Cloud Storage")
            logger.info("This could be due to authentication issues - check your GOOGLE_APPLICATION_CREDENTIALS")
            return False

    except Exception as e:
        logger.error(f"❌ Error during cloud storage test: {e}", exc_info=True)
        return False

## File: visualization_debug.py
## Location: Replace the main function

def main():
    logger.info("=== Starting Visualization Debug Tests ===")
    
    # Always test matplotlib and visualization module
    matplotlib_result = test_matplotlib_backend()
    visualization_result = test_visualization_module()
    
    # Only test cloud storage if explicitly requested
    cloud_storage_result = False
    skip_cloud_test = os.environ.get("SKIP_CLOUD_TEST", "true").lower() == "true"
    
    if skip_cloud_test:
        logger.info("Skipping cloud storage test (set SKIP_CLOUD_TEST=false to enable)")
    else:
        cloud_storage_result = test_cloud_storage()
    
    logger.info("=== Test Summary ===")
    logger.info(f"matplotlib_backend: {'✅ PASS' if matplotlib_result else '❌ FAIL'}")
    logger.info(f"visualization_module: {'✅ PASS' if visualization_result else '❌ FAIL'}")
    
    if not skip_cloud_test:
        logger.info(f"cloud_storage: {'✅ PASS' if cloud_storage_result else '❌ FAIL'}")
    else:
        logger.info("cloud_storage: ⏭️ SKIPPED")
    
    # For local development, we only need visualization to work
    if matplotlib_result and visualization_result:
        logger.info("Essential tests passed! Continue with local development.")
        return 0
    else:
        logger.error("Essential tests failed!")
        return 1

if __name__ == '__main__':
    main()
