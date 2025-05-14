# Clinical Trials Analysis Pipeline

A tool for extracting, enriching, and analyzing clinical trials data from ClinicalTrials.gov.

## Features

- Extract trials from ClinicalTrials.gov API v2
- Enrich drug information with AI-powered modality and target identification
- Analyze trends and generate visualizations
- Create comprehensive reports with quantitative and qualitative insights
- Web interface for easy access and visualization

## Setup

### Prerequisites

- Python 3.10+
- Google Cloud account (for storage and deployment)
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/clinical-trials-pipeline.git
   cd clinical-trials-pipeline

2. Create a virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies
    pip install -r requirements.txt

4. Create a .env file with credentials:
    OPENAI_API_KEY=your_openai_key
    GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
    CLOUD_STORAGE_BUCKET=your_bucket_name




