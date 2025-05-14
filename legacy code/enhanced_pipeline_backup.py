#!/usr/bin/env python
"""
Enhanced Clinical Trials Pipeline with OpenAI Integration

This script performs the pipeline functions with OpenAI enhancement:
1. Fetches clinical trials from ClinicalTrials.gov API
2. Extracts basic information
3. Uses OpenAI to determine modality and target for interventions
4. Saves results to CSV files and generates reports
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta

# Check for required packages
try:
    import requests
    print("✓ Successfully imported requests")
except ImportError:
    print("✗ requests module not found")
    print("Please install it with: pip install requests")
    sys.exit(1)

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

# Create directories
CACHE_DIR = "cache"
DATA_DIR = "data"
RESULTS_DIR = "results"
FIGURES_DIR = "figures"

for directory in [CACHE_DIR, DATA_DIR, RESULTS_DIR, FIGURES_DIR]:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

def fetch_clinical_trials(disease, industry_sponsored=True, interventional=True,
                         human_studies=True, years_back=15, max_results=None):
    """Fetch clinical trials for a disease"""
    print(f"Fetching clinical trials for {disease}")
    
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Calculate date 15 years ago for filtering
    start_date = (datetime.now() - timedelta(days=365*years_back)).strftime("%Y-%m-%d")
    
    # Build query parameters
    params = {
        "query.cond": disease,
        "pageSize": 100  # Maximum page size
    }
    
    # Add conditional filters
    if industry_sponsored:
        params["query.spons.lead.class"] = "INDUSTRY"
    
    if interventional:
        params["query.type"] = "INTR"  # Interventional studies
    
    params["query.start.min"] = start_date
    
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
        
        # Get next page if needed
        total_count = data.get("totalCount", 0)
        retrieved_count = len(studies)
        
        if total_count > retrieved_count:
            print(f"Total of {total_count} studies available, retrieved {retrieved_count} so far")
            
            # Get a second page if we need more results
            if not max_results or (max_results and max_results > retrieved_count):
                next_token = data.get("nextPageToken")
                if next_token:
                    params["pageToken"] = next_token
                    print("Fetching next page...")
                    response = requests.get(base_url, params=params)
                    if response.status_code == 200:
                        more_data = response.json()
                        more_studies = more_data.get("studies", [])
                        print(f"Received {len(more_studies)} additional studies")
                        studies.extend(more_studies)
        
        # Apply max_results limit if specified
        if max_results and len(studies) > max_results:
            studies = studies[:max_results]
        
        return studies
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
            phase = design_module.get("phases", ["Not Available"])[0] if design_module and design_module.get("phases") else "Not Available"
            
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
                except:
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

def query_openai_for_drug_info(drug_name):
    """
    Use OpenAI API to get information about a drug
    """
    if not OPENAI_AVAILABLE:
        return None
    
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
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
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
                
                return {
                    "modality": data.get("modality", "unknown"),
                    "target": data.get("target", "unknown"),
                    "confidence": data.get("confidence", "low")
                }
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

def enrich_interventions(interventions, use_openai=True):
    """
    Enrich interventions with modality and target information
    """
    print(f"Enriching {len(interventions)} interventions")
    enriched_data = []
    
    for intervention in interventions:
        try:
            # Default values
            modality = "unknown"
            target = "unknown"
            source = "Inference"
            
            # Try to get info from OpenAI if enabled
            if use_openai and OPENAI_AVAILABLE:
                print(f"Enriching {intervention} with OpenAI...")
                openai_result = query_openai_for_drug_info(intervention)
                
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
            
            enriched_data.append({
                "name": intervention,
                "modality": modality,
                "target": target,
                "source": source
            })
            
        except Exception as e:
            print(f"Error enriching {intervention}: {e}")
            # Add default data on error
            enriched_data.append({
                "name": intervention,
                "modality": "unknown",
                "target": "unknown",
                "source": "Error"
            })
    
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

def generate_summary(processed_trials, enriched_interventions):
    """
    Generate a comprehensive summary of the data
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
    
    # Save to file
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
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
    
    print(f"Saved report to {os.path.join(RESULTS_DIR, 'report.md')}")
    
    return summary

def main():
    """Run the enhanced pipeline with OpenAI integration"""
    # Set disease and parameters
    disease = "Familial Hypercholesterolemia"
    max_trials = 10  # Can be increased for more comprehensive analysis
    
    print(f"\n===== Starting Enhanced Clinical Trials Pipeline for {disease} =====\n")
    
    start_time = time.time()
    
    # Step 1: Fetch clinical trials
    raw_trials = fetch_clinical_trials(
        disease, 
        industry_sponsored=True, 
        interventional=True, 
        human_studies=True, 
        years_back=15,
        max_results=max_trials
    )
    
    if not raw_trials:
        print("No trials found. Exiting pipeline.")
        return
    
    print(f"Found {len(raw_trials)} trials from the API.")
    
    # Step 2: Process clinical trials data
    processed_trials = extract_study_details(raw_trials)
    
    # Step 3: Extract unique interventions
    unique_interventions = extract_unique_interventions(processed_trials)
    
    # Step 4: Enrich interventions with OpenAI
    use_openai = OPENAI_AVAILABLE
    enriched_interventions = enrich_interventions(unique_interventions, use_openai=use_openai)
    
    # Step 5: Save data to CSV
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
    
    # Step 6: Generate summary and report
    summary = generate_summary(processed_trials, enriched_interventions)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"\n===== Pipeline completed in {execution_time:.2f} seconds =====\n")
    
    print("Output files:")
    print(f"- Clinical trials data: {os.path.join(DATA_DIR, 'clinical_trials.csv')}")
    print(f"- Intervention data: {os.path.join(DATA_DIR, 'interventions.csv')}")
    print(f"- Summary: {os.path.join(RESULTS_DIR, 'summary.json')}")
    print(f"- Report: {os.path.join(RESULTS_DIR, 'report.md')}")

if __name__ == "__main__":
    main()
