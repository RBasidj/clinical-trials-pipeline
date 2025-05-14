echo '
import os
import sys

print("Starting test...")

# Check imports
try:
    from data_extraction import ClinicalTrialsExtractor
    print("✓ Successfully imported ClinicalTrialsExtractor")
except Exception as e:
    print(f"✗ Failed to import ClinicalTrialsExtractor: {e}")
    sys.exit(1)

try:
    extractor = ClinicalTrialsExtractor()
    print("✓ Successfully created ClinicalTrialsExtractor instance")
except Exception as e:
    print(f"✗ Failed to create ClinicalTrialsExtractor instance: {e}")
    sys.exit(1)

# Try to fetch a very small sample
try:
    print("Attempting to fetch 3 trials...")
    trials = extractor.fetch_clinical_trials("Alzheimer", max_results=3)
    print(f"✓ Successfully fetched {len(trials)} trials")
    
    if len(trials) > 0:
        print(f"Sample trial ID: {trials[0].get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'Unknown')}")
except Exception as e:
    print(f"✗ Failed to fetch trials: {e}")
    sys.exit(1)

print("Test completed successfully!")
' > test_pipeline.py