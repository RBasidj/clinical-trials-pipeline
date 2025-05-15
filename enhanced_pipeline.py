#!/usr/bin/env python
"""
Enhanced Clinical Trials Pipeline with OpenAI Integration

This script performs the pipeline functions with OpenAI enhancement:
1. Fetches clinical trials from ClinicalTrials.gov API v2
2. Extracts basic information
3. Uses OpenAI to determine modality and target for interventions
4. Saves results to CSV files and generates reports
"""
import os
import sys

# Load environment variables at the very beginning
from dotenv import load_dotenv
load_dotenv()

import json
import time
from datetime import datetime, timedelta
from visualization import create_visualizations
from analysis import generate_qualitative_insights
from financial_analysis import get_companies_from_drugs, analyze_competitive_landscape, analyze_clinical_thresholds
import concurrent.futures
import threading
import hashlib
import pickle
import time

def cache_key(func_name, args_dict):
    """Generate a cache key from function name and arguments"""
    # Convert args to a stable string representation and hash it
    args_str = str(sorted(args_dict.items()))
    return f"{func_name}_{hashlib.md5(args_str.encode()).hexdigest()}"

def cache_result(cache_dir, key, result, expiry_days=30):
    """Cache a result with expiration time"""
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{key}.pkl")
    
    # Store the result along with timestamp
    data = {
        "timestamp": time.time(),
        "expiry_days": expiry_days,
        "result": result
    }
    
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        print(f"Cached result to {cache_file}")
        return True
    except Exception as e:
        print(f"Error caching result: {e}")
        return False

def get_cached_result(cache_dir, key):
    """Retrieve a cached result if valid"""
    cache_file = os.path.join(cache_dir, f"{key}.pkl")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, "rb") as f:
            data = pickle.load(f)
        
        # Check if expired
        now = time.time()
        expiry_seconds = data["expiry_days"] * 86400  # Convert days to seconds
        if now - data["timestamp"] > expiry_seconds:
            # Cache expired
            print(f"Cache expired for {cache_file}")
            return None
        
        print(f"Retrieved cached result from {cache_file}")
        return data["result"]
    except Exception as e:
        print(f"Error reading cache: {e}")
        return None



# Check for required packages
try:
    import requests
    print("✓ Successfully imported requests")
except ImportError:
    print("✗ requests module not found")
    print("Please install it with: pip install requests")
    sys.exit(1)

try:
    import pandas as pd
    print("✓ Successfully imported pandas")
except ImportError:
    print("✗ pandas module not found")
    print("Continuing without pandas - some functionality may be limited")
    pd = None

try:
    import openai
    from dotenv import load_dotenv
    print("✓ Successfully imported openai and dotenv")
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Set OpenAI API key
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        print("⚠️ WARNING: OPENAI_API_KEY not found in environment variables")
        print("OpenAI enrichment will be skipped")
        OPENAI_AVAILABLE = False
    else:
        print("✓ OpenAI API key loaded successfully")
        OPENAI_AVAILABLE = True
except ImportError:
    print("⚠️ WARNING: openai or python-dotenv packages not found")
    print("OpenAI enrichment will be skipped")
    OPENAI_AVAILABLE = False

## File: enhanced_pipeline.py
## Location: Update the parse_arguments function

def parse_arguments():
    """Parse command line arguments for the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clinical Trials Processing & Modality/Target Analysis Pipeline')
    
    parser.add_argument('--disease', type=str, default='Familial Hypercholesterolemia',
                       help='Disease or condition to search for')
    
    parser.add_argument('--max-trials', type=int, default=100,
                       help='Maximum number of trials to process (0 for unlimited)')
    
    parser.add_argument('--years-back', type=int, default=15,
                       help='Number of years back to search for trials')
    
    parser.add_argument('--industry-only', action='store_true',
                       help='Only include industry-sponsored trials')
    
    parser.add_argument('--skip-openai', action='store_true',
                       help='Skip OpenAI enrichment (uses pattern-based only)')
    
    parser.add_argument('--skip-financial', action='store_true',
                       help='Skip financial analysis (faster processing)')
    
    parser.add_argument('--output-dir', type=str, default='.',
                       help='Directory to store output files')
    
    parser.add_argument('--run-id', type=str, default=None,
                       help='Unique identifier for this pipeline run')
    
    args = parser.parse_args()
    return args

# Create directories
CACHE_DIR = "cache"
DATA_DIR = "data"
RESULTS_DIR = "results"
FIGURES_DIR = "figures"

for directory in [CACHE_DIR, DATA_DIR, RESULTS_DIR, FIGURES_DIR]:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

## File: enhanced_pipeline.py
## Location: Replace the fetch_clinical_trials function completely

def fetch_clinical_trials(disease, industry_sponsored=True, interventional=True,
                         human_studies=True, years_back=15, max_results=None):
    """Fetch clinical trials for a disease using the v2 API with caching"""
    print(f"Fetching clinical trials for {disease}")
    
    # Generate cache key
    cache_args = {
        "disease": disease,
        "industry_sponsored": industry_sponsored,
        "interventional": interventional,
        "human_studies": human_studies,
        "years_back": years_back,
        "max_results": max_results
    }
    key = cache_key("fetch_clinical_trials", cache_args)
    
    # Check cache first
    cached_result = get_cached_result(CACHE_DIR, key)
    if cached_result is not None:
        print(f"Retrieved {len(cached_result)} trials from cache")
        return cached_result
    
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Calculate date 15 years ago for filtering
    start_date = (datetime.now() - timedelta(days=365*years_back)).strftime("%Y-%m-%d")
    
    # Build query parameters correctly for v2 API
    # Using query.titles as shown in the example code
    params = {
        "query.titles": disease,
        "pageSize": 100,
        "format": "json"
    }
    
    if industry_sponsored:
        # We do filtering in post-processing to avoid query parameter issues
        pass
        
    if interventional:
        # We do filtering in post-processing to avoid query parameter issues
        pass
    
    print(f"API request URL: {base_url}")
    print(f"Parameters: {params}")
    
    all_studies = []
    
    try:
        print(f"Making API request to {base_url}")
        response = requests.get(base_url, params=params)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            return []
        
        data = response.json()
        studies = data.get("studies", [])
        total_count = data.get("totalCount", 0)
        
        print(f"Received {len(studies)} studies from API (total available: {total_count})")
        
        # Filter studies based on criteria
        filtered_studies = []
        for study in studies:
            # Check if study meets our criteria
            if industry_sponsored:
                sponsor_module = study.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
                lead_sponsor = sponsor_module.get("leadSponsor", {})
                if lead_sponsor.get("class") != "INDUSTRY":
                    continue
            
            if interventional:
                design_module = study.get("protocolSection", {}).get("designModule", {})
                if design_module.get("studyType") != "INTERVENTIONAL":
                    continue
            
            # Check date criteria
            status_module = study.get("protocolSection", {}).get("statusModule", {})
            start_date_struct = status_module.get("startDateStruct", {})
            study_start_date = start_date_struct.get("date", "")
            
            # Add study if it passes all filters
            filtered_studies.append(study)
        
        print(f"After filtering: {len(filtered_studies)} studies match criteria")
        all_studies.extend(filtered_studies)
        
        # Get additional pages if needed
        while "nextPageToken" in data and data["nextPageToken"] and (not max_results or len(all_studies) < max_results):
            next_token = data["nextPageToken"]
            print(f"Fetching next page with token: {next_token[:10]}...")
            
            # Update token for next page
            params["pageToken"] = next_token
            
            # Make the request
            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                print(f"Error fetching next page: {response.status_code}")
                break
                
            data = response.json()
            page_studies = data.get("studies", [])
            print(f"Received {len(page_studies)} more studies")
            
            # Filter studies again
            filtered_page_studies = []
            for study in page_studies:
                # Check if study meets our criteria
                if industry_sponsored:
                    sponsor_module = study.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
                    lead_sponsor = sponsor_module.get("leadSponsor", {})
                    if lead_sponsor.get("class") != "INDUSTRY":
                        continue
                
                if interventional:
                    design_module = study.get("protocolSection", {}).get("designModule", {})
                    if design_module.get("studyType") != "INTERVENTIONAL":
                        continue
                
                # Add study if it passes all filters
                filtered_page_studies.append(study)
            
            print(f"After filtering page: {len(filtered_page_studies)} studies match criteria")
            all_studies.extend(filtered_page_studies)
            
            # Apply max_results limit if specified
            if max_results and max_results > 0 and len(all_studies) > max_results:
                all_studies = all_studies[:max_results]
            print(f"Total studies after all pages and filtering: {len(all_studies)}")

            
            # Avoid overloading the API
            time.sleep(0.5)
        
        # Apply max_results limit if not already applied
        if max_results and len(all_studies) > max_results:
            all_studies = all_studies[:max_results]
        
        print(f"Total studies after all pages and filtering: {len(all_studies)}")
        
        # Cache the result before returning
        if all_studies:
            cache_result(CACHE_DIR, key, all_studies)
        
        return all_studies
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def extract_study_details(studies):
    """Extract relevant details from each study"""
    print("Extracting study details...")
    processed_studies = []
    
    for study in studies:
        try:
            # Extract protocol section
            protocol = study.get("protocolSection", {})
            
            # Extract identification info
            identification = protocol.get("identificationModule", {})
            nct_id = identification.get("nctId")
            title = identification.get("briefTitle")
            
            # Extract status info
            status_module = protocol.get("statusModule", {})
            status = status_module.get("overallStatus") if status_module else None
            start_date = status_module.get("startDateStruct", {}).get("date") if status_module else None
            completion_date = status_module.get("completionDateStruct", {}).get("date") if status_module else None
            
            # Extract design info
            design_module = protocol.get("designModule", {})
            study_type = design_module.get("studyType") if design_module else None
            phases = design_module.get("phases", [])
            phase = phases[0] if phases else "Not Available"
            
            # Extract sponsor info
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            lead_sponsor = sponsor_module.get("leadSponsor", {}).get("name", "Unknown") if sponsor_module else "Unknown"
            
            # Extract condition info
            condition_module = protocol.get("conditionsModule", {})
            conditions = condition_module.get("conditions", []) if condition_module else []
            
            # Extract intervention info
            intervention_module = protocol.get("armsInterventionsModule", {})
            interventions = []
            
            if intervention_module:
                for intervention in intervention_module.get("interventions", []):
                    if intervention.get("type") == "DRUG":
                        interventions.append({
                            'name': intervention.get("name"),
                            'type': intervention.get("type"),
                            'description': intervention.get("description")
                        })
            
            # Extract eligibility info
            eligibility_module = protocol.get("eligibilityModule", {})
            min_age = eligibility_module.get("minimumAge") if eligibility_module else None
            max_age = eligibility_module.get("maximumAge") if eligibility_module else None
            gender = eligibility_module.get("sex") if eligibility_module else None
            
            # Extract enrollment info
            enrollment = design_module.get("enrollmentInfo", {}).get("count") if design_module else None
            
            # Extract outcome measures
            outcome_module = protocol.get("outcomesModule", {})
            primary_outcomes = []
            secondary_outcomes = []
            
            if outcome_module:
                primary_outcomes = [
                    outcome.get("measure") 
                    for outcome in outcome_module.get("primaryOutcomes", [])
                ]
                
                secondary_outcomes = [
                    outcome.get("measure") 
                    for outcome in outcome_module.get("secondaryOutcomes", [])
                ]
            
            # Calculate trial duration in days
            duration = None
            if start_date and completion_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    completion = datetime.strptime(completion_date, '%Y-%m-%d')
                    duration = (completion - start).days
                except Exception as date_error:
                    # Handle incomplete date formats (e.g., '2020-01')
                    try:
                        # Try with just year-month
                        if len(start_date) == 7 and len(completion_date) == 7:
                            start = datetime.strptime(start_date, '%Y-%m')
                            completion = datetime.strptime(completion_date, '%Y-%m')
                            duration = (completion - start).days
                    except:
                        print(f"Could not calculate duration for {nct_id}: {date_error}")
                        duration = None
            
            # Create processed study record
            processed_study = {
                'nct_id': nct_id,
                'title': title,
                'status': status,
                'phase': phase,
                'study_type': study_type,
                'start_date': start_date,
                'completion_date': completion_date,
                'duration_days': duration,
                'conditions': conditions,
                'interventions': interventions,
                'sponsor': lead_sponsor,
                'enrollment': enrollment,
                'min_age': min_age,
                'max_age': max_age,
                'gender': gender,
                'primary_outcomes': primary_outcomes,
                'secondary_outcomes': secondary_outcomes
            }
            
            processed_studies.append(processed_study)
            
        except Exception as e:
            print(f"Error processing study {study.get('nctId', 'unknown')}: {e}")
            continue
    
    print(f"Successfully processed {len(processed_studies)} studies")
    return processed_studies

def extract_unique_interventions(processed_studies):
    """
    Extract unique drug interventions from all studies
    """
    print("Extracting unique interventions...")
    unique_interventions = set()
    
    for study in processed_studies:
        for intervention in study.get("interventions", []):
            if intervention.get("type") == "DRUG" and intervention.get("name"):
                unique_interventions.add(intervention.get("name"))
    
    unique_list = list(unique_interventions)
    print(f"Found {len(unique_list)} unique drug interventions")
    return unique_list

def infer_modality_from_name(drug_name):
    """
    Infer modality based on naming conventions and patterns
    """
    if not drug_name:
        return "unknown"
        
    drug_lower = drug_name.lower()
    
    # Check for monoclonal antibody naming convention
    if any(suffix in drug_lower for suffix in ["mab", "umab", "ximab", "zumab", "imab"]):
        return "monoclonal antibody"
    
    # Check for patterns in name
    modality_patterns = {
        "small molecule": ["small molecule", "synthetic", "chemical", "inhibitor", "antagonist", "agonist"],
        "peptide": ["peptide", "protein", "polypeptide"],
        "enzyme": ["enzyme", "ase"],
        "gene therapy": ["gene", "vector", "viral", "aav"],
        "cell therapy": ["cell", "stem", "t-cell", "car-t"],
        "vaccine": ["vaccine", "vax", "immunization"],
        "oligonucleotide": ["rna", "dna", "nucleotide", "antisense", "sirna"]
    }
    
    for modality, patterns in modality_patterns.items():
        if any(pattern in drug_lower for pattern in patterns):
            return modality
    
    # Default if no pattern matches
    return "small molecule"

## File: enhanced_pipeline.py
## Location: Modify query_openai_for_drug_info function to accept a client parameter

## File: enhanced_pipeline.py
## Location: Replace the entire query_openai_for_drug_info function

def query_openai_for_drug_info(drug_name, client=None):
    """
    Use OpenAI API to get information about a drug
    Updated for OpenAI API 1.0+ with caching and client parameter for thread safety
    """
    if not OPENAI_AVAILABLE:
        return None
    
    # Generate cache key
    cache_args = {"drug_name": drug_name.lower()}  # Lowercase for consistent caching
    key = cache_key("query_openai_for_drug_info", cache_args)
    
    # Check cache first
    cached_result = get_cached_result(CACHE_DIR, key)
    if cached_result is not None:
        print(f"Retrieved OpenAI info for {drug_name} from cache")
        return cached_result
    
    try:
        print(f"Querying OpenAI for information about {drug_name}")
        
        # Create the prompt
        prompt = f"""
        I need information about the drug or intervention "{drug_name}". 
        Please determine:
        1. The modality (e.g., small molecule, monoclonal antibody, peptide, gene therapy, etc.)
        2. The primary biological target (e.g., receptor, enzyme, protein, etc.)
        
        Format your response as a JSON object with the following structure:
        {{
            "modality": "determined modality",
            "target": "determined target",
            "confidence": "high/medium/low"
        }}
        
        If you're unsure, use "unknown" for the value and "low" for confidence.
        """
        
        # Use provided client or create a new one
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant with expertise in pharmacology and drug discovery."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        # Extract response content
        content = response.choices[0].message.content
        
        # Try to parse JSON from the response
        try:
            # Find JSON object in response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
                
                result = {
                    "modality": data.get("modality", "unknown"),
                    "target": data.get("target", "unknown"),
                    "confidence": data.get("confidence", "low")
                }
                
                # Cache successful result
                cache_result(CACHE_DIR, key, result)
                
                return result
            else:
                print(f"Could not find JSON in response: {content}")
                return None
        except Exception as e:
            print(f"Error parsing OpenAI response: {e}")
            print(f"Response content: {content}")
            return None
    except Exception as e:
        print(f"Error querying OpenAI: {e}")
        return None


def enrich_interventions(interventions, use_openai=True, max_workers=5):
    """
    Enrich interventions with modality and target information using parallel processing
    """
    print(f"Enriching {len(interventions)} interventions with parallel processing")
    enriched_data = []
    
    # Use thread-local storage for OpenAI client
    local = threading.local()
    
    def get_openai_client():
        """Get or create thread-local OpenAI client"""
        if not hasattr(local, 'openai_client'):
            from openai import OpenAI
            local.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return local.openai_client
    
    def process_intervention(intervention):
        """Process a single intervention (for parallel execution)"""
        try:
            # Default values
            modality = "unknown"
            target = "unknown"
            source = "Inference"
            
            # Try to get info from OpenAI if enabled
            if use_openai and OPENAI_AVAILABLE:
                print(f"Enriching {intervention} with OpenAI...")
                
                # Use thread-local client to avoid concurrency issues
                client = get_openai_client() if OPENAI_AVAILABLE else None
                openai_result = query_openai_for_drug_info(intervention, client)
                
                if openai_result and openai_result.get("modality") != "unknown":
                    modality = openai_result.get("modality")
                    target = openai_result.get("target")
                    source = "OpenAI"
                    
                    # If confidence is low, also try pattern-based
                    if openai_result.get("confidence") == "low":
                        pattern_modality = infer_modality_from_name(intervention)
                        if pattern_modality != "unknown" and pattern_modality != modality:
                            # Use pattern-based if it differs and OpenAI is uncertain
                            modality = pattern_modality
                            source = "Inference (OpenAI low confidence)"
                else:
                    # Fallback to pattern-based inference
                    modality = infer_modality_from_name(intervention)
            else:
                # Use pattern-based inference
                modality = infer_modality_from_name(intervention)
            
            return {
                "name": intervention,
                "modality": modality,
                "target": target,
                "source": source
            }
            
        except Exception as e:
            print(f"Error enriching {intervention}: {e}")
            # Add default data on error
            return {
                "name": intervention,
                "modality": "unknown",
                "target": "unknown",
                "source": f"Error: {str(e)}"
            }
    
    # Execute in parallel if OpenAI is available and enabled
    if use_openai and OPENAI_AVAILABLE and len(interventions) > 1:
        # Use ThreadPoolExecutor for I/O-bound tasks like API calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_intervention = {
                executor.submit(process_intervention, intervention): intervention 
                for intervention in interventions
            }
            
            # Process results as they complete
            completed = 0
            for future in concurrent.futures.as_completed(future_to_intervention):
                intervention = future_to_intervention[future]
                try:
                    result = future.result()
                    enriched_data.append(result)
                    completed += 1
                    print(f"Completed enrichment of {intervention} ({completed}/{len(interventions)})")
                except Exception as e:
                    print(f"Exception processing {intervention}: {e}")
                    # Add default data on error
                    enriched_data.append({
                        "name": intervention,
                        "modality": "unknown",
                        "target": "unknown",
                        "source": f"Error: {str(e)}"
                    })
    else:
        # Process sequentially if OpenAI is not available or disabled
        print("Processing interventions sequentially")
        for idx, intervention in enumerate(interventions):
            result = process_intervention(intervention)
            enriched_data.append(result)
            print(f"Completed enrichment of {intervention} ({idx+1}/{len(interventions)})")
    
    print(f"Successfully enriched {len(enriched_data)} interventions")
    return enriched_data

def save_to_csv(data, filename, headers, directory=DATA_DIR):
    """
    Save data to CSV file
    """
    file_path = os.path.join(directory, filename)
    
    with open(file_path, "w") as f:
        # Write header
        f.write(",".join(headers) + "\n")
        
        # Write data
        for item in data:
            values = []
            for header in headers:
                value = item.get(header, "")
                
                # Handle lists
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value)
                
                # Escape commas
                if isinstance(value, str):
                    value = value.replace(",", ";")
                
                values.append(str(value))
            
            f.write(",".join(values) + "\n")
    
    print(f"Saved {len(data)} records to {file_path}")
    return file_path

def process_trials_for_summary(trials):
    """
    Process trials data for summary statistics
    """
    sponsors = {}
    phases = {}
    primary_outcomes = {}
    secondary_outcomes = {}
    enrollment_values = []
    duration_values = []
    
    for trial in trials:
        # Process sponsor
        sponsor = trial.get("sponsor")
        if sponsor:
            sponsors[sponsor] = sponsors.get(sponsor, 0) + 1
        
        # Process phase
        phase = trial.get("phase")
        if phase:
            phases[phase] = phases.get(phase, 0) + 1
        
        # Process primary outcomes
        for outcome in trial.get("primary_outcomes", []):
            if outcome:
                primary_outcomes[outcome] = primary_outcomes.get(outcome, 0) + 1
        
        # Process secondary outcomes
        for outcome in trial.get("secondary_outcomes", []):
            if outcome:
                secondary_outcomes[outcome] = secondary_outcomes.get(outcome, 0) + 1
        
        # Process enrollment
        enrollment = trial.get("enrollment")
        if enrollment and str(enrollment).isdigit():
            enrollment_values.append(int(enrollment))
        
        # Process duration
        duration = trial.get("duration_days")
        if duration and str(duration).isdigit():
            duration_values.append(int(duration))
    
    # Calculate quartiles for enrollment and duration
    enrollment_quartiles = calculate_quartiles(enrollment_values)
    duration_quartiles = calculate_quartiles(duration_values)
    
    return {
        "sponsors": sponsors,
        "phases": phases,
        "primary_outcomes": primary_outcomes,
        "secondary_outcomes": secondary_outcomes,
        "enrollment_quartiles": enrollment_quartiles,
        "duration_quartiles": duration_quartiles
    }

def calculate_quartiles(values):
    """
    Calculate quartiles for a list of values
    """
    if not values:
        return {"min": None, "q1": None, "median": None, "q3": None, "max": None}
    
    values.sort()
    n = len(values)
    
    min_val = values[0]
    max_val = values[-1]
    
    if n % 2 == 0:
        median = (values[n//2 - 1] + values[n//2]) / 2
    else:
        median = values[n//2]
    
    if n >= 4:
        if (n//4) % 2 == 0:
            q1 = (values[n//4 - 1] + values[n//4]) / 2
        else:
            q1 = values[n//4]
        
        if (3*n//4) % 2 == 0:
            q3 = (values[3*n//4 - 1] + values[3*n//4]) / 2
        else:
            q3 = values[3*n//4]
    else:
        q1 = min_val
        q3 = max_val
    
    return {
        "min": min_val,
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": max_val
    }

def generate_summary(processed_trials, enriched_interventions, qualitative_insights=None, 
                    company_analysis=None, competitive_landscape=None, threshold_analysis=None):
    """
    Generate a comprehensive summary of the data with enhanced analysis
    """
    print("Generating summary...")
    
    # Process trials
    trials_summary = process_trials_for_summary(processed_trials)
    
    # Process interventions
    modalities = {}
    targets = {}
    
    for intervention in enriched_interventions:
        # Process modality
        modality = intervention.get("modality")
        if modality and modality != "unknown":
            modalities[modality] = modalities.get(modality, 0) + 1
        
        # Process target
        target = intervention.get("target")
        if target and target != "unknown":
            targets[target] = targets.get(target, 0) + 1
    
    # Create final summary
    summary = {
        "quantitative_summary": {
            "total_trials": len(processed_trials),
            "total_interventions": len(enriched_interventions),
            "modalities": {
                "count": len(modalities),
                "list": modalities
            },
            "targets": {
                "count": len(targets),
                "list": targets
            },
            "primary_outcomes": {
                "count": len(trials_summary["primary_outcomes"]),
                "list": trials_summary["primary_outcomes"]
            },
            "secondary_outcomes": {
                "count": len(trials_summary["secondary_outcomes"]),
                "list": trials_summary["secondary_outcomes"]
            },
            "sponsors": {
                "count": len(trials_summary["sponsors"]),
                "list": trials_summary["sponsors"]
            },
            "phases": trials_summary["phases"],
            "enrollment_quartiles": trials_summary["enrollment_quartiles"],
            "duration_quartiles": trials_summary["duration_quartiles"]
        },
        "data_sources": {
            "api": "ClinicalTrials.gov API v2",
            "modality_target_sources": ["OpenAI API", "Name-based inference"]
        }
    }
    
    # Add enhanced analyses if available
    if qualitative_insights:
        summary["qualitative_insights"] = qualitative_insights
    
    if company_analysis:
        # Extract financial insights
        summary["financial_insights"] = {
            "company_count": len(set(comp.get("company") for comp in company_analysis if comp.get("company") != "Unknown")),
            "top_companies": [
                {"name": comp.get("company"), "ticker": ",".join(comp.get("tickers", []))}
                for comp in company_analysis 
                if comp.get("company") != "Unknown" and comp.get("tickers")
            ][:5]  # Top 5 companies
        }
    
    if competitive_landscape:
        summary["competitive_landscape"] = competitive_landscape
    
    if threshold_analysis:
        summary["threshold_analysis"] = threshold_analysis
    
    # Save to file
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"Saved summary to {os.path.join(RESULTS_DIR, 'summary.json')}")
    
    # Generate report markdown
    with open(os.path.join(RESULTS_DIR, "report.md"), "w") as f:
        f.write("# Clinical Trials Analysis Report\n\n")
        
        f.write("## Quantitative Summary\n\n")
        f.write(f"Total trials analyzed: {len(processed_trials)}\n")
        f.write(f"Total unique interventions: {len(enriched_interventions)}\n\n")
        
        f.write("### Modalities\n\n")
        f.write(f"Number of modalities: {len(modalities)}\n")
        for modality, count in sorted(modalities.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- {modality}: {count}\n")
        f.write("\n")
        
        f.write("### Biological Targets\n\n")
        f.write(f"Number of targets: {len(targets)}\n")
        for target, count in sorted(targets.items(), key=lambda x: x[1], reverse=True)[:10]:
            f.write(f"- {target}: {count}\n")
        if len(targets) > 10:
            f.write(f"- ... and {len(targets) - 10} more\n")
        f.write("\n")
        
        f.write("### Trial Phases\n\n")
        for phase, count in sorted(trials_summary["phases"].items(), key=lambda x: x[1], reverse=True):
            f.write(f"- {phase}: {count}\n")
        f.write("\n")
        
        f.write("### Top Sponsors\n\n")
        for sponsor, count in sorted(trials_summary["sponsors"].items(), key=lambda x: x[1], reverse=True)[:10]:
            f.write(f"- {sponsor}: {count}\n")
        if len(trials_summary["sponsors"]) > 10:
            f.write(f"- ... and {len(trials_summary['sponsors']) - 10} more\n")
        f.write("\n")
        
        f.write("### Enrollment (Patients)\n\n")
        eq = trials_summary["enrollment_quartiles"]
        f.write(f"- Minimum: {eq['min']}\n")
        f.write(f"- Q1: {eq['q1']}\n")
        f.write(f"- Median: {eq['median']}\n")
        f.write(f"- Q3: {eq['q3']}\n")
        f.write(f"- Maximum: {eq['max']}\n\n")
        
        f.write("### Trial Duration (Days)\n\n")
        dq = trials_summary["duration_quartiles"]
        f.write(f"- Minimum: {dq['min']}\n")
        f.write(f"- Q1: {dq['q1']}\n")
        f.write(f"- Median: {dq['median']}\n")
        f.write(f"- Q3: {dq['q3']}\n")
        f.write(f"- Maximum: {dq['max']}\n\n")
        
        f.write("## Qualitative Insights\n\n")
        
        # Add enhanced qualitative insights if available
        if qualitative_insights:
            f.write("### Trends in Mechanism of Action and Modality\n\n")
            for insight in qualitative_insights.get("modality_trends", []):
                f.write(f"- {insight}\n")
            f.write("\n")
            
            f.write("### Trends in Primary and Secondary Outcome Measures\n\n")
            for insight in qualitative_insights.get("outcome_trends", []):
                f.write(f"- {insight}\n")
            f.write("\n")
            
            f.write("### Observations About Trial Length and Enrollment\n\n")
            for insight in qualitative_insights.get("design_trends", []):
                f.write(f"- {insight}\n")
        else:
            f.write("### Trends in Mechanism of Action and Modality\n\n")
            f.write("- The most common modality is small molecule, which remains the dominant approach.\n")
            if "monoclonal antibody" in modalities:
                f.write("- Monoclonal antibodies represent an important therapeutic modality in the pipeline.\n")
            
            f.write("\n### Trends in Primary and Secondary Outcome Measures\n\n")
            if trials_summary["primary_outcomes"]:
                top_outcome = max(trials_summary["primary_outcomes"].items(), key=lambda x: x[1])[0]
                f.write(f"- The most common primary outcome measure is related to {top_outcome}.\n")
            
            f.write("\n### Observations About Trial Length and Enrollment\n\n")
            if dq["median"] and eq["median"]:
                f.write(f"- The median trial duration is {dq['median']} days with median enrollment of {eq['median']} participants.\n")
        
        # Add financial insights if available
        if company_analysis:
            f.write("\n## Financial and Company Analysis\n\n")
            companies = set(comp.get("company") for comp in company_analysis if comp.get("company") != "Unknown")
            f.write(f"There are {len(companies)} companies involved in the trials for this disease area.\n\n")
            
            f.write("### Key Companies with Stock Performance\n\n")
            for comp in company_analysis:
                if comp.get("company") != "Unknown" and comp.get("stock_performance"):
                    f.write(f"#### {comp.get('company')}\n")
                    f.write(f"- Drug: {comp.get('drug')}\n")
                    f.write(f"- Modality: {comp.get('modality')}\n")
                    f.write(f"- Target: {comp.get('target')}\n")
                    
                    for stock in comp.get("stock_performance", []):
                        if 'error' not in stock:
                            f.write(f"- Stock: {stock.get('ticker')} - Current Price: ${stock.get('price'):.2f}\n")
                            f.write(f"  - 1-Year Performance: {stock.get('change_1y'):.2f}%\n")
                            if stock.get('market_cap') and stock.get('market_cap') != 'Unknown':
                                f.write(f"  - Market Cap: ${stock.get('market_cap')/1e9:.2f} billion\n")
                    f.write("\n")
        
        # Add competitive landscape if available
        if competitive_landscape:
            f.write("\n## Competitive Landscape Analysis\n\n")
            for target_space in competitive_landscape:
                f.write(f"### Target: {target_space.get('target')}\n\n")
                f.write(f"- Drugs in development: {target_space.get('drugs')}\n")
                f.write(f"- Companies involved: {', '.join(target_space.get('companies'))}\n\n")
                
                f.write("| Drug | Company | Modality | Key Outcome |\n")
                f.write("|------|---------|----------|-------------|\n")
                
                for drug in target_space.get('comparative_data', []):
                    f.write(f"| {drug.get('drug')} | {drug.get('company')} | {drug.get('modality')} | {drug.get('key_outcome')} |\n")
                f.write("\n")
        
        # Add threshold analysis if available
        if threshold_analysis:
            f.write("\n## Clinical Relevance Thresholds\n\n")
            
            if 'biomarker_thresholds' in threshold_analysis.get('thresholds', {}):
                f.write("### Biomarker Thresholds\n\n")
                for threshold in threshold_analysis['thresholds']['biomarker_thresholds']:
                    f.write(f"- {threshold.get('measure')}: Minimum meaningful: {threshold.get('minimum_meaningful')}, ")
                    f.write(f"Competitive advantage: {threshold.get('competitive_advantage')}\n")
                f.write("\n")
            
            if 'threshold_relevance' in threshold_analysis and threshold_analysis['threshold_relevance'].get('notes'):
                f.write("### Relevance to Current Trials\n\n")
                for note in threshold_analysis['threshold_relevance'].get('notes', []):
                    f.write(f"- {note}\n")
                f.write("\n")
    
    print(f"Saved report to {os.path.join(RESULTS_DIR, 'report.md')}")
    
    return summary

## File: enhanced_pipeline.py
## Location: Update main function to ensure time logging

def main():
    """Run the enhanced pipeline with all enhancements"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set parameters
    disease = args.disease
    max_trials = args.max_trials
    years_back = args.years_back
    industry_sponsored = args.industry_only
    use_openai = not args.skip_openai
    skip_financial = args.skip_financial
    
    print(f"\n===== Starting Enhanced Clinical Trials Pipeline for {disease} =====\n")
    print(f"Max trials: {'Unlimited' if max_trials == 0 else max_trials}")
    print(f"Financial analysis: {'Skipped' if skip_financial else 'Enabled'}")
    
    overall_start_time = time.time()
    
    # Step 1: Fetch clinical trials with the corrected API query format
    step_start = time.time()
    raw_trials = fetch_clinical_trials(
        disease, 
        industry_sponsored=industry_sponsored, 
        interventional=True, 
        human_studies=True, 
        years_back=years_back,
        max_results=max_trials
    )
    print(f"[TIMER] Data extraction took {time.time() - step_start:.2f}s")

    if not raw_trials:
        print("No trials found. Exiting pipeline.")
        return
    
    print(f"Found {len(raw_trials)} trials from the API.")
    
    # Step 2: Process clinical trials data
    step_start = time.time()
    processed_trials = extract_study_details(raw_trials)
    print(f"[TIMER] Data processing took {time.time() - step_start:.2f}s")

    # Step 3: Extract unique interventions
    step_start = time.time()
    unique_interventions = extract_unique_interventions(processed_trials)
    print(f"[TIMER] Intervention extraction took {time.time() - step_start:.2f}s")
    
    # Step 4: Enrich interventions with OpenAI
    step_start = time.time()
    enriched_interventions = enrich_interventions(unique_interventions, use_openai=use_openai)
    print(f"[TIMER] Enrichment took {time.time() - step_start:.2f}s")

    # Step 5: Generate visualizations
    step_start = time.time()
    visualization_files = create_visualizations(processed_trials, enriched_interventions)
    print(f"[TIMER] Visualization took {time.time() - step_start:.2f}s")
    print(f"Generated {len(visualization_files)} visualization files")

    # Step 6: Generate qualitative insights
    step_start = time.time()
    qualitative_insights = generate_qualitative_insights(processed_trials, enriched_interventions)
    print(f"[TIMER] Qualitative insights took {time.time() - step_start:.2f}s")

    # Steps 7-9: Financial analysis (conditional)
    if skip_financial:
        print("Skipping financial analysis...")
        company_analysis = []
        competitive_landscape = []
        threshold_analysis = {"skipped": True}
    else:
        # Step 7: Financial/biotech specific analysis
        step_start = time.time()
        company_analysis = get_companies_from_drugs(enriched_interventions)
        print(f"[TIMER] Company analysis took {time.time() - step_start:.2f}s")

        # Step 8: Competitive landscape analysis
        step_start = time.time()
        competitive_landscape = analyze_competitive_landscape(processed_trials, company_analysis)
        print(f"[TIMER] Competitive landscape analysis took {time.time() - step_start:.2f}s")
        
        # Step 9: Threshold analysis
        step_start = time.time()
        threshold_analysis = analyze_clinical_thresholds(processed_trials, disease)
        print(f"[TIMER] Threshold analysis took {time.time() - step_start:.2f}s")

    # Step 10: Save data to CSV
    step_start = time.time()
    save_to_csv(
        processed_trials,
        "clinical_trials.csv",
        ["nct_id", "title", "status", "phase", "sponsor", "start_date", "completion_date", 
         "duration_days", "enrollment"]
    )
    
    save_to_csv(
        enriched_interventions,
        "interventions.csv",
        ["name", "modality", "target", "source"]
    )
    print(f"[TIMER] CSV generation took {time.time() - step_start:.2f}s")
    
    # Step 11: Generate final summary report with all analyses
    step_start = time.time()
    summary = generate_summary(
        processed_trials, 
        enriched_interventions,
        qualitative_insights=qualitative_insights,
        company_analysis=company_analysis,
        competitive_landscape=competitive_landscape,
        threshold_analysis=threshold_analysis
    )
    print(f"[TIMER] Summary generation took {time.time() - step_start:.2f}s")
    
    overall_execution_time = time.time() - overall_start_time
    
    print(f"\n===== Pipeline completed in {overall_execution_time:.2f} seconds =====\n")
    
    print("Output files:")
    print(f"- Clinical trials data: {os.path.join(DATA_DIR, 'clinical_trials.csv')}")
    print(f"- Intervention data: {os.path.join(DATA_DIR, 'interventions.csv')}")
    print(f"- Summary: {os.path.join(RESULTS_DIR, 'summary.json')}")
    print(f"- Report: {os.path.join(RESULTS_DIR, 'report.md')}")
    print(f"- Visualizations: {', '.join(visualization_files)}")
    
    print("\n===== Performance Summary =====")
    print(f"Total execution time: {overall_execution_time:.2f} seconds")
    
    return summary

if __name__ == "__main__":
    main()
