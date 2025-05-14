import os
import json
import subprocess
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from cloud_storage import upload_pipeline_outputs, download_pipeline_outputs, get_file_url

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'results'

# Store run information in memory (for demo purposes)
# In production, use a database
runs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_analysis', methods=['POST'])
def run_analysis():
    # Generate a unique run ID
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # Get parameters
    disease = request.form.get('disease', 'Familial Hypercholesterolemia')
    max_trials = request.form.get('max_trials', '50')
    years_back = request.form.get('years_back', '15')
    industry_only = 'industry_only' in request.form
    
    # Store run parameters
    runs[run_id] = {
        'disease': disease,
        'max_trials': max_trials,
        'years_back': years_back,
        'industry_only': industry_only,
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'files': {}
    }
    
    # Ensure output directories exist
    for directory in ['data', 'results', 'figures']:
        os.makedirs(directory, exist_ok=True)
    
    # Run the pipeline script
    cmd = [
        'python', 'enhanced_pipeline.py',
        '--disease', disease,
        '--max-trials', max_trials,
        '--years-back', years_back,
        '--run-id', run_id
    ]
    
    if industry_only:
        cmd.append('--industry-only')
    
    # Run the pipeline
    try:
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Pipeline execution failed: {result.stderr}")
            runs[run_id]['status'] = 'error'
            runs[run_id]['error'] = result.stderr
        else:
            print(f"Pipeline executed successfully: {result.stdout}")
            
            # Check if output files exist
            files_exist = False
            for directory in ['data', 'results', 'figures']:
                if os.path.exists(directory) and os.listdir(directory):
                    files_exist = True
                    break
                    
            if not files_exist:
                runs[run_id]['status'] = 'error'
                runs[run_id]['error'] = "Pipeline ran successfully but did not generate output files"
                return redirect(url_for('results', run_id=run_id))
                
            # Upload files to cloud storage
            try:
                from cloud_storage import upload_pipeline_outputs
                file_urls = upload_pipeline_outputs(run_id)
                
                if not file_urls:
                    print("Warning: No files were uploaded to cloud storage")
                    
                # Update run information
                runs[run_id]['status'] = 'completed'
                runs[run_id]['files'] = file_urls
                runs[run_id]['end_time'] = datetime.now().isoformat()
            except Exception as e:
                print(f"Error uploading files to cloud storage: {e}")
                # Still mark as completed, but note the storage error
                runs[run_id]['status'] = 'completed'
                runs[run_id]['storage_error'] = str(e)
                runs[run_id]['end_time'] = datetime.now().isoformat()
        
    except Exception as e:
        print(f"Error running pipeline: {e}")
        runs[run_id]['status'] = 'error'
        runs[run_id]['error'] = str(e)
    
    # Redirect to results page
    return redirect(url_for('results', run_id=run_id))

@app.route('/results/<run_id>')
def results(run_id):
    # Check if run exists
    if run_id not in runs:
        return "Run not found", 404
    
    run_info = runs[run_id]
    
    # If still running, show progress page
    if run_info['status'] == 'running':
        return render_template('progress.html', run_id=run_id)
    
    # If error, show error page
    if run_info['status'] == 'error':
        return render_template('error.html', run_id=run_id, error=run_info.get('error', 'Unknown error'))
    
    # Load summary data
    summary = None
    if 'results/summary.json' in run_info['files']:
        try:
            # Try to download from cloud storage
            summary_url = run_info['files']['results/summary.json']
            import requests
            response = requests.get(summary_url)
            if response.status_code == 200:
                summary = response.json()
        except Exception as e:
            print(f"Error loading summary: {e}")
    
    if not summary:
        # Fallback to local file
        try:
            with open('results/summary.json', 'r') as f:
                summary = json.load(f)
        except:
            summary = {"error": "Summary file not found"}
    
    # Extract visualization URLs
    visualizations = []
    for file_path, url in run_info['files'].items():
        if file_path.startswith('figures/') and file_path.endswith('.png'):
            # Extract filename without path
            filename = os.path.basename(file_path)
            visualizations.append({
                'name': filename.replace('.png', '').replace('_', ' ').title(),
                'url': url
            })
    
    return render_template(
        'results.html',
        run_id=run_id,
        disease=run_info['disease'],
        summary=summary,
        visualizations=visualizations,
        file_urls=run_info['files']
    )

@app.route('/api/status/<run_id>', methods=['GET'])
def run_status(run_id):
    """API endpoint to check run status"""
    if run_id not in runs:
        return jsonify({'status': 'not_found'}), 404
        
    return jsonify({
        'status': runs[run_id]['status'],
        'disease': runs[run_id]['disease'],
        'start_time': runs[run_id]['start_time'],
        'end_time': runs[run_id].get('end_time')
    })

def get_local_files(directory):
    """Get list of files in a local directory"""
    if os.path.exists(directory):
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return []

app.jinja_env.globals.update(get_local_files=get_local_files)

@app.route('/files/<path:filename>')
def files(filename):
    """Serve local files (fallback for development)"""
    return send_from_directory('results', filename)

@app.route('/figures/<path:filename>')
def figures(filename):
    """Serve local figures (fallback for development)"""
    return send_from_directory('figures', filename)

@app.route('/results/<run_id>')
def results(run_id):
    # Check if run exists
    if run_id not in runs:
        return "Run not found", 404
    
    run_info = runs[run_id]
    
    # If still running, show progress page
    if run_info['status'] == 'running':
        return render_template('progress.html', run_id=run_id)
    
    # If error, still try to show any results that might be available
    
    # Load summary data
    summary = None
    if 'files' in run_info and run_info['files'] and 'results/summary.json' in run_info['files']:
        try:
            # Try to download from cloud storage
            summary_url = run_info['files']['results/summary.json']
            import requests
            response = requests.get(summary_url)
            if response.status_code == 200:
                summary = response.json()
                print(f"Successfully loaded summary from cloud: {summary_url}")
        except Exception as e:
            print(f"Error loading summary from cloud: {e}")
    
    if not summary:
        # Fallback to local file
        try:
            with open('results/summary.json', 'r') as f:
                summary = json.load(f)
                print("Successfully loaded summary from local file")
        except Exception as e:
            print(f"Error loading local summary: {e}")
            summary = {"error": "Summary file not found"}
    
    # Extract visualization URLs
    visualizations = []
    if 'files' in run_info and run_info['files']:
        for file_path, url in run_info['files'].items():
            if file_path.startswith('figures/') and file_path.endswith('.png'):
                # Extract filename without path
                filename = os.path.basename(file_path)
                visualizations.append({
                    'name': filename.replace('.png', '').replace('_', ' ').title(),
                    'url': url
                })
                print(f"Found visualization: {file_path} -> {url}")
    
    # Check if we have visualizations
    if not visualizations:
        # If nothing in cloud storage, check local files
        if os.path.exists('figures'):
            figure_files = [f for f in os.listdir('figures') if f.endswith('.png')]
            for filename in figure_files:
                visualizations.append({
                    'name': filename.replace('.png', '').replace('_', ' ').title(),
                    'url': f"/figures/{filename}"
                })
                print(f"Found local visualization: {filename}")
    
    print(f"Rendering results with {len(visualizations)} visualizations")
    
    return render_template(
        'results.html',
        run_id=run_id,
        disease=run_info['disease'],
        summary=summary,
        visualizations=visualizations,
        file_urls=run_info.get('files', {}),
        run_info=run_info
    )

if __name__ == '__main__':
    # Create necessary directories
    for directory in ['results', 'figures', 'data']:
        os.makedirs(directory, exist_ok=True)
    
    # Get port from environment variable (for Cloud Run)
    port = int(os.environ.get('PORT', 8080))
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=port)