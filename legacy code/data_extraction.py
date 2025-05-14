import os
import sys
import json
from datetime import datetime, timedelta
import config
from utils import timer

# Try to import requests, if it fails, guide the user
try:
    import requests
    print("Successfully imported requests")
except ImportError:
    print("Error: requests module not found. Please install it with:")
    print("pip install --user requests")
    sys.exit(1)

class ClinicalTrialsExtractor:
    """
    Class for extracting clinical trials data from ClinicalTrials.gov API v2
    """
    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        print("ClinicalTrialsExtractor initialized")
    
    @timer
    def fetch_clinical_trials(self, disease, max_results=None):
        """
        Fetch clinical trials for a given disease with specified filters
        """
        print(f"Fetching clinical trials for {disease} from the real API...")
        
        # Calculate date 15 years ago for filtering
        start_date = (datetime.now() - timedelta(days=365*15)).strftime("%Y-%m-%d")
        
        # Build query parameters - simple version
        params = {
            "query.cond": disease,
            "pageSize": 5  # Start with a small page size
        }
        
        try:
            # Make a single API request
            print(f"Making API request to {self.base_url}")
            response = requests.get(self.base_url, params=params)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response content: {response.text[:500]}...")
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
    
    def extract_study_details(self, studies):
        """
        Extract relevant details from each study - simplified version
        """
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
                
                # Simple processed study record
                processed_study = {
                    "nct_id": nct_id,
                    "title": title
                }
                
                # Add status if available
                status_module = protocol.get("statusModule", {})
                if status_module:
                    processed_study["status"] = status_module.get("overallStatus")
                
                # Add phase if available
                design_module = protocol.get("designModule", {})
                if design_module and "phases" in design_module:
                    phases = design_module.get("phases", [])
                    if phases:
                        processed_study["phase"] = phases[0]
                
                # Add sponsor if available
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
                if sponsor_module and "leadSponsor" in sponsor_module:
                    processed_study["sponsor"] = sponsor_module.get("leadSponsor", {}).get("name")
                
                # Add interventions if available
                intervention_module = protocol.get("armsInterventionsModule", {})
                if intervention_module and "interventions" in intervention_module:
                    interventions = []
                    for intervention in intervention_module.get("interventions", []):
                        if intervention.get("type") == "DRUG":
                            interventions.append({
                                "name": intervention.get("name"),
                                "type": intervention.get("type")
                            })
                    processed_study["interventions"] = interventions
                
                processed_studies.append(processed_study)
                
            except Exception as e:
                print(f"Error processing study {study.get('nctId', 'unknown')}: {e}")
                continue
        
        print(f"Successfully processed {len(processed_studies)} studies")
        return processed_studies
    
    def extract_unique_interventions(self, processed_studies):
        """
        Extract unique drug interventions from all studies
        """
        print("Extracting unique interventions...")
        unique_interventions = set()
        
        for study in processed_studies:
            for intervention in study.get("interventions", []):
                if intervention.get("type") == "DRUG":
                    unique_interventions.add(intervention.get("name"))
        
        unique_list = list(unique_interventions)
        print(f"Found {len(unique_list)} unique drug interventions")
        return unique_list
    
    def save_to_csv(self, processed_studies, output_file=None):
        """
        Save processed studies to CSV file - simplified version
        """
        if output_file is None:
            output_file = os.path.join(config.DATA_DIR, "clinical_trials.csv")
        
        # Create a simple CSV manually
        with open(output_file, "w") as f:
            # Write header
            f.write("nct_id,title,status,phase,sponsor\n")
            
            # Write data
            for study in processed_studies:
                nct_id = study.get("nct_id", "")
                title = study.get("title", "").replace(",", ";")  # Replace commas in title
                status = study.get("status", "")
                phase = study.get("phase", "")
                sponsor = study.get("sponsor", "").replace(",", ";")  # Replace commas in sponsor
                
                f.write(f"{nct_id},{title},{status},{phase},{sponsor}\n")
        
        print(f"Saved {len(processed_studies)} studies to {output_file}")
        return processed_studies
