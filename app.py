import os
import json
import subprocess
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from cloud_storage import upload_pipeline_outputs, download_pipeline_outputs, get_file_url

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

    runs[run_id] = {
        'disease': disease,
        'max_trials': max_trials,
        'years_back': years_back,
        'industry_only': industry_only,
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'files': {}
    }

    for directory in ['data', 'results', 'figures']:
        os.makedirs(directory, exist_ok=True)

    cmd = [
        'python', 'enhanced_pipeline.py',
        '--disease', disease,
        '--max-trials', max_trials,
        '--years-back', years_back,
        '--run-id', run_id
    ]

    if industry_only:
        cmd.append('--industry-only')

    try:
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Pipeline execution failed: {result.stderr}")
            runs[run_id]['status'] = 'error'
            runs[run_id]['error'] = result.stderr
        else:
            print(f"Pipeline executed successfully: {result.stdout}")

            files_exist = any(
                os.path.exists(d) and os.listdir(d) for d in ['data', 'results', 'figures']
            )

            if not files_exist:
                runs[run_id]['status'] = 'error'
                runs[run_id]['error'] = "Pipeline ran successfully but did not generate output files"
                return redirect(url_for('results', run_id=run_id))

            try:
                file_urls = upload_pipeline_outputs(run_id)
                runs[run_id]['status'] = 'completed'
                runs[run_id]['files'] = file_urls
                runs[run_id]['end_time'] = datetime.now().isoformat()
            except Exception as e:
                print(f"Error uploading files to cloud storage: {e}")
                runs[run_id]['status'] = 'completed'
                runs[run_id]['storage_error'] = str(e)
                runs[run_id]['end_time'] = datetime.now().isoformat()

    except Exception as e:
        print(f"Error running pipeline: {e}")
        runs[run_id]['status'] = 'error'
        runs[run_id]['error'] = str(e)

    return redirect(url_for('results', run_id=run_id))

@app.route('/results/<run_id>')
def results(run_id):
    try:
        if run_id not in runs:
            print(f"Run not found: {run_id}")
            return render_template('error.html',
                                   error=f"Run ID {run_id} not found",
                                   run_id=run_id,
                                   run_info={"disease": "Unknown"})

        run_info = runs[run_id]
        print(f"Processing results for run_id: {run_id}, status: {run_info['status']}")

        if run_info['status'] == 'running':
            return render_template('progress.html', run_id=run_id)

        summary = None
        summary_source = None

        try:
            if 'results/summary.json' in run_info.get('files', {}):
                summary_url = run_info['files']['results/summary.json']
                print(f"Attempting to load summary from cloud: {summary_url}")
                import requests
                response = requests.get(summary_url, timeout=10)
                if response.status_code == 200:
                    summary = response.json()
                    summary_source = "cloud"
                    print(f"Successfully loaded summary from cloud")
                else:
                    print(f"Failed to load cloud summary, status: {response.status_code}")
        except Exception as e:
            print(f"Error loading summary from cloud: {e}")

        if not summary:
            try:
                with open('results/summary.json', 'r') as f:
                    summary = json.load(f)
                    summary_source = "local"
                    print(f"Successfully loaded summary from local file")
            except Exception as e:
                print(f"Error loading local summary: {e}")
                summary = {"error": "Summary file not found or invalid"}
                summary_source = "error"

        visualizations = []
        viz_source = None

        if 'files' in run_info and run_info['files']:
            print(f"Checking cloud storage for visualizations")
            for file_path, url in run_info['files'].items():
                if 'figures/' in file_path and file_path.endswith('.png'):
                    filename = os.path.basename(file_path)
                    name = filename.replace('.png', '').replace('_', ' ').title()
                    visualizations.append({'name': name, 'url': url})
                    print(f"Found cloud visualization: {name} -> {url}")
            viz_source = "cloud" if visualizations else "none"

        if not visualizations:
            print("Checking local directory for visualizations")
            figure_dir = 'figures'
            if os.path.exists(figure_dir):
                for filename in os.listdir(figure_dir):
                    if filename.endswith('.png'):
                        name = filename.replace('.png', '').replace('_', ' ').title()
                        url = url_for('figures', filename=filename)
                        visualizations.append({'name': name, 'url': url})
                        print(f"Found local visualization: {name} -> {url}")
                viz_source = "local" if visualizations else "none"

        run_info['debug'] = {
            'summary_source': summary_source,
            'visualization_source': viz_source,
            'visualization_count': len(visualizations)
        }

        print(f"Rendering results with {len(visualizations)} visualizations from {viz_source}")
        print(f"[DEBUG] Visualizations being passed: {visualizations}")

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
        print(f"Unhandled exception in results route: {e}")
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

    return jsonify({
        'status': runs[run_id]['status'],
        'disease': runs[run_id]['disease'],
        'start_time': runs[run_id]['start_time'],
        'end_time': runs[run_id].get('end_time')
    })

def get_local_files(directory):
    if os.path.exists(directory):
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return []

app.jinja_env.globals.update(get_local_files=get_local_files)

@app.route('/files/<path:filename>')
def files(filename):
    return send_from_directory('results', filename)

@app.route('/figures/<path:filename>')
def figures(filename):
    return send_from_directory('figures', filename)

if __name__ == '__main__':
    for directory in ['results', 'figures', 'data']:
        os.makedirs(directory, exist_ok=True)
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
