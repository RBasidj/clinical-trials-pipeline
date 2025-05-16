# Clinical Trials Analysis Pipeline

An advanced tool for extracting, enriching, and analyzing clinical trials data from ClinicalTrials.gov with modality/target analysis and financial intelligence.

## Features

- Extract trials from ClinicalTrials.gov API v2
- Enrich drug information with AI-powered modality and target identification
- Generate comprehensive visualizations of trial data
- Analyze financial metrics and competitive landscape
- Create detailed reports with quantitative and qualitative insights
- Web interface for easy access and visualization

## Prerequisites

- Python 3.10+
- Pip package manager
- 2GB+ free disk space
- Internet connection (for API access)
- OpenAI API key (optional, for enhanced enrichment)
- Google Cloud account (optional, for cloud deployment)

## Local Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/clinical-trials-pipeline.git
cd clinical-trials-pipeline
```

2. Create and activate a virtual environment:

```bash
python -m venv trials_venv

# On Windows:
trials_venv\Scripts\activate

# On macOS/Linux:
source trials_venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key_here
CLOUD_STORAGE_BUCKET=your_bucket_name
FORCE_LOCAL_FILES=true
```

> **Note**: If you don't have an OpenAI API key, the system will fall back to pattern-based inference, which is less accurate but still functional.

## Running the Pipeline Locally

### Using the Command Line Interface

For direct analysis without the web interface:

```bash
python enhanced_pipeline.py --disease "Familial Hypercholesterolemia" --max-trials 50 --years-back 15
```

#### Command Line Arguments:

- `--disease`: Disease or condition to search for (default: "Familial Hypercholesterolemia")
- `--max-trials`: Maximum number of trials to process (default: 100, use 0 for unlimited)
- `--years-back`: Number of years to look back (default: 15)
- `--industry-only`: Only include industry-sponsored trials
- `--skip-openai`: Skip OpenAI enrichment (uses pattern-based inference only)
- `--skip-financial`: Skip financial analysis (faster processing)

### Using the Web Interface

Start the Flask web server:

```bash
python app.py
```

Then open your browser and navigate to:

```
http://127.0.0.1:8080
```

Enter analysis parameters in the web form:

- Disease/condition
- Maximum trials to analyze
- Years to look back
- Industry-only toggle
- Financial analysis toggle

Click **"Run Analysis"** and wait for the results.

## Output Files

The pipeline generates multiple output files in these directories:

### `data/`: Contains raw data in CSV format
- `clinical_trials.csv`: Processed trials data
- `interventions.csv`: Enriched interventions data

### `results/`: Contains analysis outputs
- `summary.json`: Structured analysis results
- `report.md`: Markdown report with findings
- `report.txt`: Plain text version of the report

### `figures/`: Contains visualization images
- `modality_distribution.png`: Distribution of drug modalities
- `trial_timeline.png`: Timeline of trial start dates
- `enrollment_distribution.png`: Distribution of trial sizes
- Other visualizations based on the data

## Customizing the Analysis

### Different Diseases/Conditions

To analyze a different disease or condition:

```bash
python enhanced_pipeline.py --disease "Diabetes Type 2"
```

Or use the web interface to enter any disease of interest.

### Limiting Results

For faster analysis with fewer trials:

```bash
python enhanced_pipeline.py --disease "Alzheimer's Disease" --max-trials 25
```

### Focusing on Recent Data

To analyze only more recent trials:

```bash
python enhanced_pipeline.py --disease "COVID-19" --years-back 5
```

## Troubleshooting

### OpenAI API Issues

If you encounter OpenAI API errors:

- Verify your API key in the `.env` file
- Run without OpenAI enrichment:

```bash
python enhanced_pipeline.py --disease "Your Disease" --skip-openai
```

### Cloud Storage Issues

For local development, the pipeline defaults to local file storage. If you encounter cloud storage errors:

- Set `FORCE_LOCAL_FILES=true` in your `.env` file
- Or use the diagnostic route in the web interface:  
  ```
  http://127.0.0.1:8080/diagnose_storage
  ```

### Missing Visualizations

If visualizations are not appearing:

- Check if the `figures/` directory exists and contains PNG files
- Ensure `matplotlib` is installed correctly:
  
```bash
pip install matplotlib
```

- Try running without financial analysis which may timeout:

```bash
--skip-financial
```

### Common Error Messages

- `"No downloadable files are available"`: Files are only accessible locally, not from cloud storage
- `"Error in financial analysis section"`: Skip financial analysis with `--skip-financial`
- `"Failed to initialize storage"`: Set `FORCE_LOCAL_FILES=true` in `.env`

## Performance Optimization

For larger analyses:

- Limit the number of trials: `--max-trials 50`
- Skip financial analysis: `--skip-financial`
- Use pattern-based inference: `--skip-openai`

## Cloud Deployment

This pipeline can be deployed to Google Cloud Run for web-based access:

1. Ensure you have the Google Cloud SDK installed

2. Configure your project:

```bash
gcloud config set project your-project-id
```

3. Deploy using the provided script:

```bash
python deploy_cloud.py
```

The deployment script accepts parameters for resource allocation:

```bash
python deploy_cloud.py --memory=4Gi --cpu=2 --timeout=60m
```

Upon successful deployment, you'll receive a URL where the application is accessible.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for enhanced enrichment
- `CLOUD_STORAGE_BUCKET`: Google Cloud Storage bucket name
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account key file
- `FORCE_LOCAL_FILES`: Set to `"true"` to bypass cloud storage
- `REPORT_GENERATION_TIMEOUT`: Timeout in seconds for report generation (default: 30)
- `DEBUG_LEVEL`: Logging level (`INFO`, `DEBUG`, etc.)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
