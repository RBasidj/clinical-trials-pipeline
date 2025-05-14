import os
import config

class InterventionEnricher:
    """Simple enricher for demo purposes"""
    
    def __init__(self):
        # Modality classification patterns
        self.modality_patterns = {
            "small molecule": ["small molecule", "synthetic", "chemical", "inhibitor", "antagonist", "agonist"],
            "monoclonal antibody": ["antibody", "mab", "monoclonal", "umab", "ximab", "zumab", "olimab"],
            "peptide": ["peptide", "protein", "polypeptide"],
            "enzyme": ["enzyme", "ase"],
            "gene therapy": ["gene", "vector", "viral", "aav"],
            "cell therapy": ["cell", "stem", "t-cell", "car-t"],
            "vaccine": ["vaccine", "vax", "immunization"],
            "oligonucleotide": ["rna", "dna", "nucleotide", "antisense", "sirna"]
        }
        print("InterventionEnricher initialized")
    
    def infer_modality_from_name(self, drug_name):
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
        for modality, patterns in self.modality_patterns.items():
            if any(pattern in drug_lower for pattern in patterns):
                return modality
        
        # Default if no pattern matches
        return "small molecule"
    
    def enrich_interventions(self, interventions):
        """Enrich interventions with modality based on name patterns"""
        print(f"Enriching {len(interventions)} interventions")
        
        enriched_data = []
        for intervention in interventions:
            modality = self.infer_modality_from_name(intervention)
            
            enriched_data.append({
                "name": intervention,
                "modality": modality,
                "target": "unknown"
            })
        
        print(f"Enriched {len(enriched_data)} interventions")
        return enriched_data
    
    def save_to_csv(self, enriched_data, output_file=None):
        """Simulate saving to CSV"""
        if output_file is None:
            output_file = os.path.join(config.DATA_DIR, "interventions.csv")
        
        print(f"Saving {len(enriched_data)} interventions to {output_file}")
        
        # Create a CSV file
        with open(output_file, "w") as f:
            f.write("name,modality,target\n")
            for item in enriched_data:
                name = item["name"].replace(",", ";") if item["name"] else ""
                modality = item["modality"]
                target = item["target"]
                f.write(f"{name},{modality},{target}\n")
        
        print(f"Saved {len(enriched_data)} interventions to {output_file}")
        return enriched_data
