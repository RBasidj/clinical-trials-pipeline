import os
import json
import subprocess
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from cloud_storage import upload_pipeline_outputs, download_pipeline_outputs, get_file_url
import logging
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'results'

# Store run information in memory
runs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_analysis', methods=['POST'])
def run_analysis():
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    disease = request.form.get('disease', 'Familial Hypercholesterolemia')
    max_trials = request.form.get('max_trials', '50')
    years_back = request.form.get('years_back', '15')
    industry_only = 'industry_only' in request.form
    financial_analysis = 'financial_analysis' in request.form

    runs[run_id] = {
        'disease': disease,
        'max_trials': max_trials,
        'years_back': years_back,
        'industry_only': industry_only,
        'financial_analysis': financial_analysis,
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'files': {},
        'progress': {
            'step': 0,
            'message': 'Initializing pipeline...',
            'percent': 0
        }
    }

    for directory in ['data', 'results', 'figures']:
        os.makedirs(directory, exist_ok=True)

    # Start the pipeline process in a background thread to avoid blocking
    cmd = [
        'python', 'enhanced_pipeline.py',
        '--disease', disease,
        '--max-trials', max_trials,
        '--years-back', years_back,
        '--run-id', run_id
    ]

    if industry_only:
        cmd.append('--industry-only')
        
    # FIX: Use --skip-financial when financial analysis is NOT selected
    if not financial_analysis:
        cmd.append('--skip-financial')

    # Start a background thread to run the pipeline
    def run_pipeline_process():
        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Update progress
            runs[run_id]['progress'] = {
                'step': 1,
                'message': 'Fetching clinical trials from API...',
                'percent': 10
            }
            
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Pipeline execution failed: {result.stderr}")
                runs[run_id]['status'] = 'error'
                runs[run_id]['error'] = result.stderr
            else:
                logger.info(f"Pipeline executed successfully: {result.stdout}")

                # Update progress
                runs[run_id]['progress'] = {
                    'step': 5,
                    'message': 'Processing complete, preparing results...',
                    'percent': 90
                }

                files_exist = any(
                    os.path.exists(d) and os.listdir(d) for d in ['data', 'results', 'figures']
                )

                if not files_exist:
                    runs[run_id]['status'] = 'error'
                    runs[run_id]['error'] = "Pipeline ran successfully but did not generate output files"
                else:
                    try:
                        file_urls = upload_pipeline_outputs(run_id)
                        runs[run_id]['status'] = 'completed'
                        runs[run_id]['files'] = file_urls
                        runs[run_id]['end_time'] = datetime.now().isoformat()
                        
                        # Update progress
                        runs[run_id]['progress'] = {
                            'step': 6,
                            'message': 'Analysis complete!',
                            'percent': 100
                        }
                    except Exception as e:
                        logger.error(f"Error uploading files to cloud storage: {e}")
                        runs[run_id]['status'] = 'completed'
                        runs[run_id]['storage_error'] = str(e)
                        runs[run_id]['end_time'] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error running pipeline: {e}")
            runs[run_id]['status'] = 'error'
            runs[run_id]['error'] = str(e)

    # Start the thread
    import threading
    thread = threading.Thread(target=run_pipeline_process)
    thread.daemon = True
    thread.start()
    
    # Add to the run_analysis function in app.py, right before returning the redirect

    # Add timeout handling and report verification
    report_timeout = 30  # seconds
    start_check_time = time.time()
    report_found = False

    # Check if the report has been generated
    report_path = os.path.join('results', 'report.md')
    while time.time() - start_check_time < report_timeout:
        if os.path.exists(report_path):
            report_size = os.path.getsize(report_path)
            print(f"Final report found: {report_path} (size: {report_size} bytes)")
            report_found = True
            break
        else:
            print(f"Waiting for report generation... ({int(time.time() - start_check_time)} seconds elapsed)")
            time.sleep(2)

    if not report_found:
        print(f"WARNING: Report not found after {report_timeout} seconds. Proceeding anyway.")
        
        # Create a fallback report if needed
        try:
            with open(report_path, 'w') as f:
                f.write("# Analysis Report\n\n")
                f.write(f"This is a fallback report for {disease}.\n\n")
                f.write("The detailed report generation timed out, but the analysis data is still available.\n")
            print(f"Created fallback report at {report_path}")
        except Exception as e:
            print(f"Error creating fallback report: {e}")

    # Check all output files
    for directory in ['data', 'results', 'figures']:
        if os.path.exists(directory):
            files = os.listdir(directory)
            print(f"Files in {directory}: {', '.join(files)}")
        else:
            print(f"Directory not found: {directory}")

    # Add debugging information to the run info
    runs[run_id]['debug_info'] = {
        'report_found': report_found,
        'execution_time': time.time() - runs[run_id].get('start_time_epoch', 0),
        'files_found': {
            'data': os.path.exists(os.path.join('data', 'clinical_trials.csv')),
            'interventions': os.path.exists(os.path.join('data', 'interventions.csv')),
            'summary': os.path.exists(os.path.join('results', 'summary.json')),
            'report': os.path.exists(os.path.join('results', 'report.md'))
        }
    }

    # Immediately redirect to the progress page
    return redirect(url_for('progress', run_id=run_id))
    
@app.route('/progress/<run_id>')
def progress(run_id):
    if run_id not in runs:
        return render_template('error.html',
                               error=f"Run ID {run_id} not found",
                               run_id=run_id,
                               run_info={"disease": "Unknown"})
    
    run_info = runs[run_id]
    disease = run_info['disease']
    
    # If process already completed, redirect to results
    if run_info['status'] != 'running':
        return redirect(url_for('results', run_id=run_id))
    
    return render_template('progress.html', 
                          run_id=run_id, 
                          disease=disease, 
                          run_info=run_info)

@app.route('/results/<run_id>')
def results(run_id):
    try:
        if run_id not in runs:
            logger.warning(f"Run not found: {run_id}")
            return render_template('error.html',
                                   error=f"Run ID {run_id} not found",
                                   run_id=run_id,
                                   run_info={"disease": "Unknown"})

        run_info = runs[run_id]
        logger.info(f"Processing results for run_id: {run_id}, status: {run_info['status']}")

        if run_info['status'] == 'running':
            return redirect(url_for('progress', run_id=run_id))

        summary = None
        summary_source = None

        try:
            if 'results/summary.json' in run_info.get('files', {}):
                summary_url = run_info['files']['results/summary.json']
                logger.info(f"Attempting to load summary from cloud: {summary_url}")
                import requests
                response = requests.get(summary_url, timeout=10)
                if response.status_code == 200:
                    summary = response.json()
                    summary_source = "cloud"
                    logger.info(f"Successfully loaded summary from cloud")
                else:
                    logger.warning(f"Failed to load cloud summary, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error loading summary from cloud: {e}")

        if not summary:
            try:
                with open('results/summary.json', 'r') as f:
                    summary = json.load(f)
                    summary_source = "local"
                    logger.info(f"Successfully loaded summary from local file")
            except Exception as e:
                logger.error(f"Error loading local summary: {e}")
                summary = {"error": "Summary file not found or invalid"}
                summary_source = "error"

        # Generate qualitative insights on-the-fly if missing
        if summary and 'qualitative_insights' not in summary:
            try:
                from analysis import generate_qualitative_insights
                
                # Load processed trials and enriched interventions data
                processed_trials = []
                enriched_interventions = []
                
                try:
                    import pandas as pd
                    if os.path.exists('data/clinical_trials.csv'):
                        processed_trials = pd.read_csv('data/clinical_trials.csv').to_dict('records')
                    if os.path.exists('data/interventions.csv'):
                        enriched_interventions = pd.read_csv('data/interventions.csv').to_dict('records')
                except Exception as e:
                    logger.error(f"Error loading CSV data: {e}")
                    
                # Generate insights if we have data
                if processed_trials and enriched_interventions:
                    qualitative_insights = generate_qualitative_insights(processed_trials, enriched_interventions)
                    summary['qualitative_insights'] = qualitative_insights
                    logger.info(f"Generated qualitative insights on-the-fly")
            except Exception as e:
                logger.error(f"Error generating qualitative insights: {e}")
                summary['qualitative_insights'] = {
                    "modality_trends": ["Analysis not available - could not generate trends"],
                    "outcome_trends": ["Analysis not available - could not generate outcome trends"],
                    "design_trends": ["Analysis not available - could not generate design insights"]
                }

        # In app.py, modify the visualization filtering in the results route
        visualizations = []
        viz_source = None

        if 'files' in run_info and run_info['files']:
            print(f"Checking cloud storage for visualizations")
            for file_path, url in run_info['files'].items():
                if ('figures/' in file_path and file_path.endswith('.png') and 
                    'test_cloud_storage' not in file_path and 'test' not in file_path):
                    filename = os.path.basename(file_path)
                    name = filename.replace('.png', '').replace('_', ' ').title()
                    visualizations.append({'name': name, 'url': url})
                    print(f"Found cloud visualization: {name} -> {url}")
            viz_source = "cloud" if visualizations else "none"

        if not visualizations:
            logger.info("Checking local directory for visualizations")
            figure_dir = 'figures'
            if os.path.exists(figure_dir):
                for filename in os.listdir(figure_dir):
                    if filename.endswith('.png'):
                        name = filename.replace('.png', '').replace('_', ' ').title()
                        url = url_for('figures', filename=filename)
                        visualizations.append({'name': name, 'url': url})
                        logger.info(f"Found local visualization: {name} -> {url}")
                viz_source = "local" if visualizations else "none"

        run_info['debug'] = {
            'summary_source': summary_source,
            'visualization_source': viz_source,
            'visualization_count': len(visualizations)
        }

        logger.info(f"Rendering results with {len(visualizations)} visualizations from {viz_source}")
        logger.debug(f"Visualizations being passed: {visualizations}")

        return render_template(
            'results.html',
            run_id=run_id,
            disease=run_info['disease'],
            summary=summary,
            visualizations=visualizations,
            file_urls=run_info.get('files', {}),
            run_info=run_info
        )

    except Exception as e:
        logger.error(f"Unhandled exception in results route: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return render_template('error.html',
                               error=f"An unexpected error occurred: {str(e)}",
                               run_id=run_id,
                               run_info={"disease": "Error loading run information"})

@app.route('/api/status/<run_id>', methods=['GET'])
def run_status(run_id):
    if run_id not in runs:
        return jsonify({'status': 'not_found'}), 404

    run_info = runs[run_id]
    
    # Create response with detailed status
    response = {
        'status': run_info['status'],
        'disease': run_info['disease'],
        'start_time': run_info['start_time'],
        'end_time': run_info.get('end_time'),
        'progress': run_info.get('progress', {
            'step': 0,
            'message': 'Initializing...',
            'percent': 0
        })
    }
    
    # If there's an error, include it
    if 'error' in run_info:
        response['error'] = run_info['error']
    
    # Include log snippets if available
    if 'log_entries' in run_info:
        response['log_entries'] = run_info.get('log_entries', [])[-5:]  # Last 5 log entries

    return jsonify(response)

def get_local_files(directory):
    if os.path.exists(directory):
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return []

app.jinja_env.globals.update(get_local_files=get_local_files)

@app.route('/files/<path:filename>')
def files(filename):
    return send_from_directory('results', filename)

@app.route('/api/debug_report/<run_id>', methods=['GET'])
def debug_report(run_id):
    """Endpoint to debug and fix report generation issues"""
    if run_id not in runs:
        return jsonify({'status': 'not_found', 'message': f'Run ID {run_id} not found'}), 404
    
    run_info = runs[run_id]
    
    # Check if report exists in cloud storage
    from cloud_storage import check_result_exists, add_empty_report
    
    report_exists = check_result_exists(run_id, 'report.md')
    
    # If report doesn't exist, create an empty one
    if not report_exists:
        success = add_empty_report(run_id)
        if success:
            return jsonify({
                'status': 'fixed',
                'message': 'Created placeholder report',
                'run_id': run_id
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create placeholder report',
                'run_id': run_id
            })
    
    return jsonify({
        'status': 'ok',
        'message': 'Report already exists',
        'run_id': run_id
    })
    
@app.route('/figures/<path:filename>')
def figures(filename):
    return send_from_directory('figures', filename)

if __name__ == '__main__':
    for directory in ['results', 'figures', 'data']:
        os.makedirs(directory, exist_ok=True)
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)