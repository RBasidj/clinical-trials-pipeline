"""
Visualization generation for clinical trials data.
"""
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import numpy as np
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_visualizations(processed_trials, enriched_interventions, output_dir="figures"):
    """Create visualizations for the clinical trials data"""
    logger.info(f"Starting visualization generation in {output_dir}")
    
    # Set style
    plt.style.use('ggplot')
    sns.set(font_scale=1.2)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    visualization_files = []
    
    try:
        # 1. Modality Distribution Pie Chart
        logger.info("Creating modality distribution pie chart")
        modalities = [intervention.get('modality', 'unknown') for intervention in enriched_interventions 
                     if intervention.get('modality') != 'unknown']
        
        if modalities:
            modality_counts = Counter(modalities)
            
            plt.figure(figsize=(10, 7))
            plt.pie(modality_counts.values(), labels=modality_counts.keys(), autopct='%1.1f%%', 
                    shadow=True, startangle=140)
            plt.title('Distribution of Intervention Modalities')
            plt.axis('equal')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'modality_distribution.png')
            plt.savefig(file_path, dpi=300)
            plt.close()
            visualization_files.append(file_path)
            logger.info(f"Saved {file_path}")
        else:
            logger.warning("No modality data available for visualization")
        
        # 2. Trial Timeline (Start Dates)
        logger.info("Creating trial timeline visualization")
        # Extract and convert dates
        dates = []
        for trial in processed_trials:
            start_date = trial.get('start_date')
            if start_date:
                try:
                    # Handle different date formats
                    if len(start_date) == 10:  # YYYY-MM-DD
                        date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    elif len(start_date) == 7:  # YYYY-MM
                        date_obj = datetime.strptime(start_date, '%Y-%m')
                    else:
                        continue
                    dates.append(date_obj)
                except Exception as e:
                    logger.error(f"Error parsing date '{start_date}': {e}")
                    continue
        
        if dates:
            plt.figure(figsize=(12, 6))
            plt.hist(dates, bins=15, color='skyblue', edgecolor='black')
            plt.title('Distribution of Trial Start Dates')
            plt.xlabel('Year')
            plt.ylabel('Number of Trials')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'trial_timeline.png')
            plt.savefig(file_path, dpi=300)
            plt.close()
            visualization_files.append(file_path)
            logger.info(f"Saved {file_path}")
        else:
            logger.warning("No date data available for timeline visualization")
        
        # 3. Enrollment Distribution
        logger.info("Creating enrollment distribution visualization")
        enrollments = [int(trial.get('enrollment')) for trial in processed_trials 
                      if trial.get('enrollment') and str(trial.get('enrollment')).isdigit()]
        
        if enrollments:
            plt.figure(figsize=(10, 6))
            sns.histplot(enrollments, kde=True, bins=10)
            plt.title('Distribution of Trial Enrollment')
            plt.xlabel('Number of Patients')
            plt.ylabel('Frequency')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'enrollment_distribution.png')
            plt.savefig(file_path, dpi=300)
            plt.close()
            visualization_files.append(file_path)
            logger.info(f"Saved {file_path}")
        else:
            logger.warning("No enrollment data available for visualization")
        
        # 4. Trial Duration vs. Enrollment Scatter Plot
        logger.info("Creating duration vs enrollment scatter plot")
        durations = []
        enrolls = []
        
        for trial in processed_trials:
            duration = trial.get('duration_days')
            enrollment = trial.get('enrollment')
            
            if duration and enrollment and str(duration).isdigit() and str(enrollment).isdigit():
                durations.append(int(duration))
                enrolls.append(int(enrollment))
        
        if durations and enrolls:
            plt.figure(figsize=(10, 6))
            plt.scatter(durations, enrolls, alpha=0.7)
            plt.title('Trial Duration vs. Enrollment')
            plt.xlabel('Trial Duration (Days)')
            plt.ylabel('Number of Patients')
            plt.grid(True)
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'duration_vs_enrollment.png')
            plt.savefig(file_path, dpi=300)
            plt.close()
            visualization_files.append(file_path)
            logger.info(f"Saved {file_path}")
        else:
            logger.warning("No duration/enrollment data available for scatter plot")
        
        # 5. Top Sponsors Bar Chart
        logger.info("Creating top sponsors bar chart")
        sponsor_counts = Counter([trial.get('sponsor') for trial in processed_trials if trial.get('sponsor')])
        top_sponsors = dict(sponsor_counts.most_common(10))
        
        if top_sponsors:
            plt.figure(figsize=(12, 8))
            plt.barh(list(top_sponsors.keys()), list(top_sponsors.values()), color='skyblue')
            plt.title('Top 10 Trial Sponsors')
            plt.xlabel('Number of Trials')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'top_sponsors.png')
            plt.savefig(file_path, dpi=300)
            plt.close()
            visualization_files.append(file_path)
            logger.info(f"Saved {file_path}")
        else:
            logger.warning("No sponsor data available for bar chart")
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
    
    logger.info(f"Created {len(visualization_files)} visualizations in {output_dir}")
    return visualization_files