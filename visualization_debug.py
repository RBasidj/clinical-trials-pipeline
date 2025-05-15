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

def test_cloud_storage():
    """Test cloud storage upload and retrieval"""
    logger.info("Testing cloud storage...")

    try:
        sys.path.append('.')
        from cloud_storage import initialize_storage, upload_pipeline_outputs, get_file_url

        test_run_id = "debug_run"
        test_dir = 'test_figures'
        os.makedirs(test_dir, exist_ok=True)

        # Create a dummy file
        dummy_file_path = os.path.join(test_dir, 'dummy_plot.png')
        plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6])
        plt.title("Dummy Plot")
        plt.savefig(dummy_file_path)
        plt.close()

        # Upload test files
        logger.info(f"Uploading test files for run_id: {test_run_id}")
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
            return False

    except Exception as e:
        logger.error(f"❌ Error during cloud storage test: {e}", exc_info=True)
        return False

def main():
    logger.info("=== Starting Visualization Debug Tests ===")
    results = {
        'matplotlib_backend': test_matplotlib_backend(),
        'visualization_module': test_visualization_module(),
        'cloud_storage': test_cloud_storage()
    }

    logger.info("=== Test Summary ===")
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{name}: {status}")

if __name__ == '__main__':
    main()
