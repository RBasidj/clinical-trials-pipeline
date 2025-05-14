import os
import json
import config

# Try to import optional dependencies
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Warning: pandas and/or matplotlib not available. Visualizations will be simplified.")

class ClinicalTrialsAnalyzer:
    """Simple analyzer for demo purposes"""
    
    def __init__(self):
        self.figures_dir = config.FIGURES_DIR
        os.makedirs(self.figures_dir, exist_ok=True)
        print("ClinicalTrialsAnalyzer initialized")
    
    def load_data(self, trials_file=None, interventions_file=None):
        """Load data from CSV files"""
        if trials_file is None:
            trials_file = os.path.join(config.DATA_DIR, "clinical_trials.csv")
        
        if interventions_file is None:
            interventions_file = os.path.join(config.DATA_DIR, "interventions.csv")
        
        print(f"Loading data from {trials_file} and {interventions_file}")
        
        # Load data differently based on available packages
        if PLOTTING_AVAILABLE:
            # Use pandas if available
            trials_df = pd.read_csv(trials_file) if os.path.exists(trials_file) else pd.DataFrame()
            interventions_df = pd.read_csv(interventions_file) if os.path.exists(interventions_file) else pd.DataFrame()
            print(f"Loaded {len(trials_df)} trials and {len(interventions_df)} interventions")
            return trials_df, interventions_df
        else:
            # Fallback to simple file reading
            trials_data = []
            interventions_data = []
            
            if os.path.exists(trials_file):
                with open(trials_file, "r") as f:
                    lines = f.readlines()
                    headers = lines[0].strip().split(",")
                    for line in lines[1:]:
                        values = line.strip().split(",")
                        trial = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
                        trials_data.append(trial)
            
            if os.path.exists(interventions_file):
                with open(interventions_file, "r") as f:
                    lines = f.readlines()
                    headers = lines[0].strip().split(",")
                    for line in lines[1:]:
                        values = line.strip().split(",")
                        intervention = {headers[i]: values[i] for i in range(min(len(headers), len(values)))}
                        interventions_data.append(intervention)
            
            print(f"Loaded {len(trials_data)} trials and {len(interventions_data)} interventions")
            return trials_data, interventions_data
    
    def generate_quantitative_summary(self):
        """Generate summary statistics"""
        print("Generating summary")
        
        # Load data
        trials_data, interventions_data = self.load_data()
        
        # Create a basic summary
        if PLOTTING_AVAILABLE:
            # Use pandas if available
            summary = {
                "total_trials": len(trials_data),
                "sponsors": list(trials_data["sponsor"].dropna().unique())[:10] if "sponsor" in trials_data.columns else [],
                "phases": trials_data["phase"].value_counts().to_dict() if "phase" in trials_data.columns else {}
            }
            
            # Add modality counts if available
            if isinstance(interventions_data, pd.DataFrame) and "modality" in interventions_data.columns:
                summary["modalities"] = interventions_data["modality"].value_counts().to_dict()
        else:
            # Simple fallback
            sponsors = set()
            phases = {}
            modalities = {}
            
            for trial in trials_data:
                if "sponsor" in trial:
                    sponsors.add(trial["sponsor"])
                
                if "phase" in trial:
                    phase = trial["phase"]
                    phases[phase] = phases.get(phase, 0) + 1
            
            for intervention in interventions_data:
                if "modality" in intervention:
                    modality = intervention["modality"]
                    modalities[modality] = modalities.get(modality, 0) + 1
            
            summary = {
                "total_trials": len(trials_data),
                "sponsors": list(sponsors)[:10],
                "phases": phases,
                "modalities": modalities
            }
        
        # Save to file
        with open(os.path.join(config.RESULTS_DIR, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"Saved summary to {os.path.join(config.RESULTS_DIR, 'summary.json')}")
        return summary
    
    def generate_visualizations(self):
        """Generate visualizations"""
        print("Generating visualizations")
        
        # Create a simple visualization
        if PLOTTING_AVAILABLE:
            # Load data
            trials_data, interventions_data = self.load_data()
            
            # Create and save a simple visualization if we have data
            if isinstance(trials_data, pd.DataFrame) and not trials_data.empty and "phase" in trials_data.columns:
                plt.figure(figsize=(10, 6))
                trials_data["phase"].value_counts().plot(kind="bar")
                plt.title("Clinical Trials by Phase")
                plt.xlabel("Phase")
                plt.ylabel("Count")
                plt.tight_layout()
                plt.savefig(os.path.join(self.figures_dir, "phases_chart.png"))
                plt.close()
                print(f"Saved visualization to {os.path.join(self.figures_dir, 'phases_chart.png')}")
            
            # Create a modality visualization if we have that data
            if isinstance(interventions_data, pd.DataFrame) and not interventions_data.empty and "modality" in interventions_data.columns:
                plt.figure(figsize=(10, 6))
                interventions_data["modality"].value_counts().plot(kind="pie", autopct="%1.1f%%")
                plt.title("Intervention Modalities")
                plt.axis("equal")
                plt.tight_layout()
                plt.savefig(os.path.join(self.figures_dir, "modalities_chart.png"))
                plt.close()
                print(f"Saved visualization to {os.path.join(self.figures_dir, 'modalities_chart.png')}")
        else:
            # Create a dummy file if visualization packages aren't available
            with open(os.path.join(self.figures_dir, "dummy_chart.txt"), "w") as f:
                f.write("Visualization packages (pandas, matplotlib) not available.\n")
                f.write("Install these packages for proper visualizations.\n")
            print(f"Created dummy chart at {os.path.join(self.figures_dir, 'dummy_chart.txt')}")
    
    def generate_qualitative_insights(self):
        """Generate qualitative insights"""
        print("Generating insights")
        
        # Load data
        trials_data, interventions_data = self.load_data()
        
        # Create basic insights
        if PLOTTING_AVAILABLE and isinstance(trials_data, pd.DataFrame) and not trials_data.empty:
            # More sophisticated insights if pandas is available
            insights = {
                "modality_trends": [],
                "outcome_trends": [],
                "trial_evolution": []
            }
            
            # Add some modality insights
            if isinstance(interventions_data, pd.DataFrame) and not interventions_data.empty and "modality" in interventions_data.columns:
                modality_counts = interventions_data["modality"].value_counts()
                top_modality = modality_counts.index[0] if not modality_counts.empty else "unknown"
                insights["modality_trends"].append(f"The most common modality is {top_modality} with {modality_counts.iloc[0]} interventions.")
            else:
                insights["modality_trends"].append("No modality data available for analysis.")
            
            # Add trial phase insights
            if "phase" in trials_data.columns:
                phase_counts = trials_data["phase"].value_counts()
                top_phase = phase_counts.index[0] if not phase_counts.empty else "unknown"
                insights["outcome_trends"].append(f"The most common trial phase is {top_phase} with {phase_counts.iloc[0]} trials.")
            else:
                insights["outcome_trends"].append("No phase data available for analysis.")
            
            # Add sponsor insights
            if "sponsor" in trials_data.columns:
                sponsor_counts = trials_data["sponsor"].value_counts()
                top_sponsor = sponsor_counts.index[0] if not sponsor_counts.empty else "unknown"
                insights["trial_evolution"].append(f"The most active sponsor is {top_sponsor} with {sponsor_counts.iloc[0]} trials.")
            else:
                insights["trial_evolution"].append("No sponsor data available for analysis.")
        else:
            # Simple fallback
            insights = {
                "modality_trends": ["Based on the available data, no clear trends in modality usage were identified."],
                "outcome_trends": [f"The dataset contains clinical trials for analysis."],
                "trial_evolution": ["To analyze trial evolution over time, more data processing is needed."]
            }
        
        # Save to markdown
        with open(os.path.join(config.RESULTS_DIR, "insights.md"), "w") as f:
            f.write("# Clinical Trials Analysis: Qualitative Insights\n\n")
            
            f.write("## Trends in Mechanism of Action and Modality Over Time\n\n")
            for insight in insights["modality_trends"]:
                f.write(f"- {insight}\n")
            f.write("\n")
            
            f.write("## Trends in Primary and Secondary Outcome Measures Over Time\n\n")
            for insight in insights["outcome_trends"]:
                f.write(f"- {insight}\n")
            f.write("\n")
            
            f.write("## Observations About Trial Length and Enrollment Evolution\n\n")
            for insight in insights["trial_evolution"]:
                f.write(f"- {insight}\n")
        
        print(f"Saved insights to {os.path.join(config.RESULTS_DIR, 'insights.md')}")
        return insights
