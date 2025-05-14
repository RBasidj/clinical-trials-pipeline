import argparse
import sys
import os
import config
from utils import create_directories, timer

# Check if required modules are available
try:
    from data_extraction import ClinicalTrialsExtractor
    from data_enrichment import InterventionEnricher
    from data_analysis import ClinicalTrialsAnalyzer
except ImportError as e:
    print(f"Error: {e}")
    print("Make sure all required files are in the current directory.")
    sys.exit(1)

@timer
def run_pipeline(disease, max_trials=None):
    """
    Run the complete pipeline for a given disease
    """
    print("\n===== Starting Clinical Trials Analysis Pipeline =====\n")
    print(f"Analyzing disease: {disease}")
    print(f"Maximum trials limit: {max_trials if max_trials else 'None'}")
    
    # Create necessary directories
    create_directories()
    
    # Initialize components
    extractor = ClinicalTrialsExtractor()
    enricher = InterventionEnricher()
    analyzer = ClinicalTrialsAnalyzer()
    
    # Step 1: Extract clinical trials from the real API
    print("\n=== Step 1: Extracting Clinical Trials ===\n")
    raw_trials = extractor.fetch_clinical_trials(
        disease, 
        max_results=max_trials
    )
    print(f"Found {len(raw_trials)} trials from the API.")
    
    if not raw_trials:
        print("No trials found. Exiting pipeline.")
        return {
            "trials": [],
            "interventions": [],
            "summary": {},
            "insights": {}
        }
    
    # Process clinical trials data
    processed_trials = extractor.extract_study_details(raw_trials)
    trials_df = extractor.save_to_csv(processed_trials)
    
    # Step 2: Extract unique interventions
    print("\n=== Step 2: Extracting Unique Interventions ===\n")
    unique_interventions = extractor.extract_unique_interventions(processed_trials)
    print(f"Found {len(unique_interventions)} unique interventions.")
    
    # Step 3: Enrich interventions
    print("\n=== Step 3: Enriching Interventions ===\n")
    enriched_interventions = enricher.enrich_interventions(unique_interventions)
    interventions_df = enricher.save_to_csv(enriched_interventions)
    
    # Step 4: Analyze data
    print("\n=== Step 4: Analyzing Data ===\n")
    analyzer.load_data()
    
    # Generate quantitative summary
    summary = analyzer.generate_quantitative_summary()
    
    # Generate visualizations
    analyzer.generate_visualizations()
    
    # Generate qualitative insights
    insights = analyzer.generate_qualitative_insights()
    
    print("\n===== Pipeline Completed Successfully =====\n")
    
    # Print output locations
    print("Output files:")
    print(f"- Clinical trials data: {os.path.join(config.DATA_DIR, 'clinical_trials.csv')}")
    print(f"- Intervention data: {os.path.join(config.DATA_DIR, 'interventions.csv')}")
    print(f"- Summary: {os.path.join(config.RESULTS_DIR, 'summary.json')}")
    print(f"- Insights: {os.path.join(config.RESULTS_DIR, 'insights.md')}")
    print(f"- Visualizations: {config.FIGURES_DIR}/*.png")
    
    return {
        "trials": processed_trials,
        "interventions": enriched_interventions,
        "summary": summary,
        "insights": insights
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clinical Trials Analysis Pipeline")
    parser.add_argument("--disease", type=str, default=config.DEFAULT_DISEASE,
                        help=f"Disease to analyze (default: {config.DEFAULT_DISEASE})")
    parser.add_argument("--max-trials", type=int, default=None,
                        help="Maximum number of trials to process (default: all)")
    
    args = parser.parse_args()
    
    # Run the pipeline
    results = run_pipeline(
        disease=args.disease,
        max_trials=args.max_trials
    )
