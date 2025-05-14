"""
Debug script to test visualization generation.
"""
import os
import json
import sys
from visualization import create_visualizations

def load_data():
    """Load processed trials and interventions from files"""
    try:
        with open('data/clinical_trials.csv', 'r') as f:
            header = f.readline().strip().split(',')
            trials = []
            for line in f:
                values = line.strip().split(',')
                trial = {header[i]: values[i] for i in range(min(len(header), len(values)))}
                trials.append(trial)
            print(f"Loaded {len(trials)} trials from CSV")
    except Exception as e:
        print(f"Error loading trials: {e}")
        # Try loading from JSON
        try:
            with open('results/summary.json', 'r') as f:
                data = json.load(f)
                trials = data.get('trials', [])
                print(f"Loaded {len(trials)} trials from JSON")
        except Exception as e2:
            print(f"Error loading trials from JSON: {e2}")
            trials = []
    
    try:
        with open('data/interventions.csv', 'r') as f:
            header = f.readline().strip().split(',')
            interventions = []
            for line in f:
                values = line.strip().split(',')
                intervention = {header[i]: values[i] for i in range(min(len(header), len(values)))}
                interventions.append(intervention)
            print(f"Loaded {len(interventions)} interventions from CSV")
    except Exception as e:
        print(f"Error loading interventions: {e}")
        # Try loading from JSON
        try:
            with open('results/summary.json', 'r') as f:
                data = json.load(f)
                interventions = data.get('interventions', [])
                print(f"Loaded {len(interventions)} interventions from JSON")
        except:
            interventions = []
    
    return trials, interventions

def main():
    """Run visualization generation as a standalone process"""
    print("Visualization Debug Tool")
    print("=======================")
    
    # Ensure output directories exist
    os.makedirs('figures', exist_ok=True)
    
    # Load data
    print("Loading data...")
    trials, interventions = load_data()
    
    if not trials or not interventions:
        print("ERROR: Could not load the required data.")
        print("Make sure you have run the pipeline first to generate data files.")
        return 1
    
    # Generate visualizations
    print("Generating visualizations...")
    try:
        visualization_files = create_visualizations(trials, interventions)
        print(f"Successfully created {len(visualization_files)} visualization files:")
        for file in visualization_files:
            print(f"  - {file}")
    except Exception as e:
        print(f"Error generating visualizations: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())