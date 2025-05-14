#!/usr/bin/env python
"""
Minimal Clinical Trials Pipeline

This script performs the basic pipeline functions with minimal dependencies:
1. Fetches clinical trials from ClinicalTrials.gov API
2. Extracts basic information
3. Uses a simple method to infer modality
4. Saves results to CSV files
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta

# Check for requests
try:
    import requests
    print("✓ Successfully imported requests")
except ImportError:
    print("✗ requests module not found")
    print("Please install it with: pip install requests")
    sys.exit(1)

# Create directories
CACHE_DIR = "cache"
DATA_DIR = "data"
RESULTS_DIR = "results"

for directory in [CACHE_DIR, DATA_DIR, RESULTS_DIR]:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

def fetch_clinical_trials(disease, max_results=None):
    """Fetch clinical trials for a disease"""
    print(f"Fetching clinical trials for {disease}")
    
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Build query parameters
    params = {
        "query.cond": disease,
        "pageSize": 5  # Small page size
    }
    
    try:
        print(f"Making API request to {base_url}")
        response = requests.get(base_url, params=params)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return []
        
        data = response.json()
        studies = data.get("studies", [])
        
        print(f"Received {len(studies)} studies from API")
        
        # Apply max_results limit if specified
        if max_results and len(studies) > max_results:
            studies = studies[:max_results]
        
        return studies
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def extract_study_details(studies):
    """Extract basic details from studies"""
    processed_studies = []
    
    for study in studies:
        try:
            # Extract protocol section
            protocol = study.get("protocolSection", {})
            
            # Get basic identification info
            identification = protocol.get("identificationModule", {})
            nct_id = identification.get("nctId")
            title = identification.get("briefTitle")
            
            # Get status info
            status_module = protocol.get("statusModule", {})
            status = status_module.get("overallStatus") if status_module else None
            
            # Get sponsor info
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            sponsor = sponsor_module.get("leadSponsor", {}).get("name") if sponsor_module else None
            
            # Get interventions
            interventions = []
            arms_module = protocol.get("armsInterventionsModule", {})
            if arms_module:
                for intervention in arms_module.get("interventions", []):
                    if intervention.get("type") == "DRUG":
                        interventions.append({
                            "name": intervention.get("name"),
                            "type": intervention.get("type")
                        })
            
            # Create processed study
            processed_study = {
                "nct_id": nct_id,
                "title": title,
                "status": status,
                "sponsor": sponsor,
                "interventions": interventions
            }
            
            processed_studies.append(processed_study)
            
        except Exception as e:
            print(f"Error processing study: {e}")
    
    print(f"Processed {len(processed_studies)} studies")
    return processed_studies

def extract_interventions(processed_studies):
    """Extract unique interventions"""
    unique_interventions = set()
    
    for study in processed_studies:
        for intervention in study.get("interventions", []):
            if intervention.get("name"):
                unique_interventions.add(intervention.get("name"))
    
    intervention_list = list(unique_interventions)
    print(f"Found {len(intervention_list)} unique interventions")
    return intervention_list

def infer_modality(drug_name):
    """Infer modality from drug name"""
    if not drug_name:
        return "unknown"
        
    drug_lower = drug_name.lower()
    
    # Check for monoclonal antibody
    if any(suffix in drug_lower for suffix in ["mab", "umab", "ximab", "zumab", "imab"]):
        return "monoclonal antibody"
    
    # Check for other patterns
    modality_patterns = {
        "small molecule": ["small", "molecule", "inhibitor", "antagonist", "agonist"],
        "peptide": ["peptide", "protein", "polypeptide"],
        "enzyme": ["enzyme", "ase"],
        "gene therapy": ["gene", "vector", "viral", "aav"],
        "vaccine": ["vaccine", "vax"]
    }
    
    for modality, patterns in modality_patterns.items():
        if any(pattern in drug_lower for pattern in patterns):
            return modality
    
    # Default
    return "small molecule"

def enrich_interventions(interventions):
    """Enrich interventions with modality"""
    enriched_data = []
    
    for name in interventions:
        modality = infer_modality(name)
        enriched_data.append({
            "name": name,
            "modality": modality,
            "target": "unknown"
        })
    
    print(f"Enriched {len(enriched_data)} interventions")
    return enriched_data

def save_to_csv(data, filename, headers):
    """Save data to CSV file"""
    file_path = os.path.join(DATA_DIR, filename)
    
    with open(file_path, "w") as f:
        # Write headers
        f.write(",".join(headers) + "\n")
        
        # Write data rows
        for item in data:
            values = []
            for header in headers:
                value = item.get(header, "")
                if isinstance(value, str):
                    # Escape commas
                    value = value.replace(",", ";")
                elif isinstance(value, list):
                    # Combine lists
                    value = "; ".join(str(v) for v in value)
                values.append(str(value))
            f.write(",".join(values) + "\n")
    
    print(f"Saved {len(data)} records to {file_path}")
    return file_path

def save_summary(processed_studies, enriched_interventions):
    """Create and save a summary"""
    # Extract high-level info
    sponsors = set()
    statuses = {}
    modalities = {}
    
    for study in processed_studies:
        if study.get("sponsor"):
            sponsors.add(study.get("sponsor"))
        
        status = study.get("status")
        if status:
            statuses[status] = statuses.get(status, 0) + 1
    
    for intervention in enriched_interventions:
        modality = intervention.get("modality")
        if modality:
            modalities[modality] = modalities.get(modality, 0) + 1
    
    summary = {
        "total_trials": len(processed_studies),
        "unique_interventions": len(enriched_interventions),
        "sponsors": list(sponsors),
        "trial_statuses": statuses,
        "modalities": modalities
    }
    
    # Save to JSON
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"Saved summary to {os.path.join(RESULTS_DIR, 'summary.json')}")
    
    # Also save a simple text report
    with open(os.path.join(RESULTS_DIR, "report.txt"), "w") as f:
        f.write("Clinical Trials Analysis Report\n")
        f.write("=============================\n\n")
        f.write(f"Total trials analyzed: {len(processed_studies)}\n")
        f.write(f"Unique interventions found: {len(enriched_interventions)}\n\n")
        
        f.write("Trial Statuses:\n")
        for status, count in statuses.items():
            f.write(f"  {status}: {count}\n")
        f.write("\n")
        
        f.write("Intervention Modalities:\n")
        for modality, count in modalities.items():
            f.write(f"  {modality}: {count}\n")
        f.write("\n")
        
        f.write("Top Sponsors:\n")
        for sponsor in list(sponsors)[:10]:
            f.write(f"  {sponsor}\n")
    
    print(f"Saved report to {os.path.join(RESULTS_DIR, 'report.txt')}")
    
    return summary

def main():
    """Run the pipeline"""
    disease = "Familial Hypercholesterolemia"
    max_trials = 3
    
    print(f"\n=== Starting Clinical Trials Pipeline for {disease} ===\n")
    
    # Fetch trials
    start_time = time.time()
    raw_trials = fetch_clinical_trials(disease, max_trials)
    if not raw_trials:
        print("No trials found. Exiting.")
        return
    
    # Process trials
    processed_trials = extract_study_details(raw_trials)
    
    # Get interventions
    interventions = extract_interventions(processed_trials)
    
    # Enrich interventions
    enriched_interventions = enrich_interventions(interventions)
    
    # Save results
    save_to_csv(
        processed_trials, 
        "clinical_trials.csv", 
        ["nct_id", "title", "status", "sponsor"]
    )
    
    save_to_csv(
        enriched_interventions, 
        "interventions.csv", 
        ["name", "modality", "target"]
    )
    
    # Save summary
    save_summary(processed_trials, enriched_interventions)
    
    end_time = time.time()
    print(f"\n=== Pipeline completed in {end_time - start_time:.2f} seconds ===\n")
    print(f"Results saved in the '{DATA_DIR}' and '{RESULTS_DIR}' directories")

if __name__ == "__main__":
    main()
