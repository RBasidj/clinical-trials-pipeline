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
import pandas as pd
from textwrap import wrap
import scipy

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_acronym(name, max_length=10):
    """Create an acronym or shortened version of a long name."""
    if not isinstance(name, str):
        return str(name)
    
    # If name is already short enough, return it
    if len(name) <= max_length:
        return name
    
    # Check if it's multiple words to create an acronym
    words = name.split()
    if len(words) > 1:
        # Create acronym from first letter of each word
        acronym = ''.join(word[0].upper() for word in words)
        if len(acronym) <= max_length:
            return acronym
    
    # If not multiple words or acronym is still too long, truncate with ellipsis
    return name[:max_length-3] + '...'

def handle_outliers(data, column, method='iqr', threshold=1.5):
    """Identify outliers in the data without removing them."""
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
        
    if column not in data.columns:
        logger.warning(f"Column '{column}' not found in data")
        return pd.Series(), (None, None)
    
    # Convert to numeric, handling non-numeric values
    data[column] = pd.to_numeric(data[column], errors='coerce')
    
    if method == 'iqr':
        q1 = data[column].quantile(0.25)
        q3 = data[column].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        # Identify outliers for special handling
        outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)][column]
        normal_range = (lower_bound, upper_bound)
        
        return outliers, normal_range
    
    elif method == 'zscore':
        from scipy import stats
        z_scores = np.abs(stats.zscore(data[column].dropna()))
        outliers = data[column][z_scores > threshold]
        
        # Calculate normal range as mean ± threshold*std
        mean = data[column].mean()
        std = data[column].std()
        normal_range = (mean - threshold*std, mean + threshold*std)
        
        return outliers, normal_range
    
    return pd.Series(), (data[column].min(), data[column].max())

# In visualization.py, modify the create_visualizations function

# Instead of completely handling outliers or long names, 
# let's add a simple flag to skip these enhancements on cloud:

def create_visualizations(processed_trials, enriched_interventions, output_dir="figures"):
    """Create visualizations for the clinical trials data"""
    logger.info(f"Starting visualization generation in {output_dir}")
    
    # Simple cloud detection
    is_cloud = os.environ.get('K_SERVICE') is not None
    
    # Set style
    plt.style.use('ggplot')
    sns.set(font_scale=1.2)
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Verify the matplotlib backend
    logger.info(f"Using matplotlib backend: {matplotlib.get_backend()}")
    
    visualization_files = []
    
    try:
        # 1. Modality Distribution Pie Chart
        logger.info("Creating modality distribution pie chart")
        modalities = [intervention.get('modality', 'unknown') for intervention in enriched_interventions 
                     if intervention.get('modality') != 'unknown']
        
        if modalities:
            modality_counts = Counter(modalities)
            
            # SIMPLIFIED: Skip acronym creation for cloud to avoid memory issues
            plt.figure(figsize=(10, 7))
            plt.pie(modality_counts.values(), labels=modality_counts.keys(), autopct='%1.1f%%', 
                    shadow=True, startangle=140)
            plt.title('Distribution of Intervention Modalities')
            plt.axis('equal')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'modality_distribution.png')
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
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
                        logger.warning(f"Skipping invalid date format: {start_date}")
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
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
        else:
            logger.warning("No date data available for timeline visualization")
        
        # 3. Enrollment Distribution
        logger.info("Creating enrollment distribution visualization")
        enrollments = [int(trial.get('enrollment')) for trial in processed_trials 
                      if trial.get('enrollment') and str(trial.get('enrollment')).isdigit()]
        
        if enrollments:
            df = pd.DataFrame({'enrollment': enrollments})
            outliers, normal_range = handle_outliers(df, 'enrollment')
            
            plt.figure(figsize=(10, 6))
            
            # Plot main histogram using the normal range
            main_data = df[(df['enrollment'] >= normal_range[0]) & 
                           (df['enrollment'] <= normal_range[1])]
            
            if not main_data.empty:
                sns.histplot(main_data['enrollment'], kde=True, bins=10)
                
                # Add text annotation about outliers if any exist
                if not outliers.empty:
                    outlier_text = f"Note: {len(outliers)} outlier(s) not shown in main plot.\n"
                    outlier_text += f"Max value: {df['enrollment'].max()}, Min value: {df['enrollment'].min()}"
                    plt.annotate(outlier_text, xy=(0.5, 0.97), xycoords='axes fraction', 
                                ha='center', va='top', bbox=dict(boxstyle="round,pad=0.5", 
                                                               fc="white", alpha=0.8))
            
            plt.title('Distribution of Trial Enrollment')
            plt.xlabel('Number of Patients')
            plt.ylabel('Frequency')
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'enrollment_distribution.png')
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            # Create a separate plot for outliers if they exist
            if not outliers.empty and len(outliers) > 0:
                plt.figure(figsize=(10, 6))
                sns.histplot(df['enrollment'], kde=True, bins=10)
                plt.title('Distribution of Trial Enrollment (Including Outliers)')
                plt.xlabel('Number of Patients')
                plt.ylabel('Frequency')
                plt.tight_layout()
                file_path_with_outliers = os.path.join(output_dir, 'enrollment_distribution_with_outliers.png')
                plt.savefig(file_path_with_outliers, dpi=300, bbox_inches='tight')
                plt.close()
                
                if os.path.exists(file_path_with_outliers):
                    visualization_files.append(file_path_with_outliers)
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
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
            df = pd.DataFrame({'duration': durations, 'enrollment': enrolls})
            
            # Handle outliers for both axes
            duration_outliers, duration_range = handle_outliers(df, 'duration')
            enrollment_outliers, enrollment_range = handle_outliers(df, 'enrollment')
            
            plt.figure(figsize=(10, 6))
            
            # Filter data to show plot without extreme outliers
            main_data = df[
                (df['duration'] >= duration_range[0]) & 
                (df['duration'] <= duration_range[1]) &
                (df['enrollment'] >= enrollment_range[0]) & 
                (df['enrollment'] <= enrollment_range[1])
            ]
            
            plt.scatter(main_data['duration'], main_data['enrollment'], alpha=0.7)
            
            # Add annotation about outliers
            outlier_count = len(df) - len(main_data)
            if outlier_count > 0:
                outlier_text = f"{outlier_count} outlier(s) not shown. "
                outlier_text += f"Full duration range: {min(durations)}-{max(durations)} days. "
                outlier_text += f"Full enrollment range: {min(enrolls)}-{max(enrolls)} patients."
                
                # Wrap text for better display
                outlier_text = '\n'.join(wrap(outlier_text, 60))
                
                plt.annotate(outlier_text, xy=(0.5, 0.02), xycoords='axes fraction', 
                            ha='center', va='bottom', bbox=dict(boxstyle="round,pad=0.5", 
                                                              fc="white", alpha=0.8),
                            fontsize=8)
            
            plt.title('Trial Duration vs. Enrollment')
            plt.xlabel('Trial Duration (Days)')
            plt.ylabel('Number of Patients')
            plt.grid(True)
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'duration_vs_enrollment.png')
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            # Create full plot with outliers
            if outlier_count > 0:
                plt.figure(figsize=(10, 6))
                plt.scatter(df['duration'], df['enrollment'], alpha=0.7)
                plt.title('Trial Duration vs. Enrollment (Including Outliers)')
                plt.xlabel('Trial Duration (Days)')
                plt.ylabel('Number of Patients')
                plt.grid(True)
                plt.tight_layout()
                file_path_with_outliers = os.path.join(output_dir, 'duration_vs_enrollment_with_outliers.png')
                plt.savefig(file_path_with_outliers, dpi=300, bbox_inches='tight')
                plt.close()
                
                if os.path.exists(file_path_with_outliers):
                    visualization_files.append(file_path_with_outliers)
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
        else:
            logger.warning("No duration/enrollment data available for scatter plot")
        
        # 5. Top Sponsors Bar Chart
        logger.info("Creating top sponsors bar chart")
        sponsor_counts = Counter([trial.get('sponsor') for trial in processed_trials if trial.get('sponsor')])
        top_sponsors = dict(sponsor_counts.most_common(10))
        
        if top_sponsors:
            # Shorten long sponsor names
            shortened_sponsors = {}
            mapping = {}
            
            for sponsor, count in top_sponsors.items():
                if len(sponsor) > 25:  # Threshold for shortening
                    short_name = create_acronym(sponsor, 25)
                    shortened_sponsors[short_name] = count
                    mapping[short_name] = sponsor
                else:
                    shortened_sponsors[sponsor] = count
            
            plt.figure(figsize=(12, 8))
            
            # Sort by count
            sponsors = {k: shortened_sponsors[k] for k in sorted(shortened_sponsors, 
                                                               key=shortened_sponsors.get, 
                                                               reverse=True)}
            
            plt.barh(list(sponsors.keys()), list(sponsors.values()), color='skyblue')
            plt.title('Top 10 Trial Sponsors')
            plt.xlabel('Number of Trials')
            
            # Add legend if we have shortened names
            if mapping:
                legend_text = '\n'.join([f"{short}: {full}" for short, full in mapping.items()])
                plt.figtext(0.05, 0.02, legend_text, fontsize=8, 
                           bbox=dict(facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'top_sponsors.png')
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
        else:
            logger.warning("No sponsor data available for bar chart")
        
        # 6. Target Distribution Bar Chart
        logger.info("Creating target distribution chart")
        targets = [intervention.get('target', 'unknown') for intervention in enriched_interventions 
                  if intervention.get('target') and intervention.get('target') != 'unknown']
        
        if targets:
            target_counts = Counter(targets)
            top_targets = dict(target_counts.most_common(10))
            
            # Shorten long target names
            shortened_targets = {}
            mapping = {}
            
            for target, count in top_targets.items():
                if len(target) > 20:  # Threshold for shortening
                    short_name = create_acronym(target, 20)
                    shortened_targets[short_name] = count
                    mapping[short_name] = target
                else:
                    shortened_targets[target] = count
            
            plt.figure(figsize=(12, 8))
            
            # Sort by count
            targets_sorted = {k: shortened_targets[k] for k in sorted(shortened_targets, 
                                                                    key=shortened_targets.get, 
                                                                    reverse=True)}
            
            plt.barh(list(targets_sorted.keys()), list(targets_sorted.values()), color='lightgreen')
            plt.title('Top 10 Biological Targets')
            plt.xlabel('Number of Interventions')
            
            # Add legend if we have shortened names
            if mapping:
                legend_text = '\n'.join([f"{short}: {full}" for short, full in mapping.items()])
                plt.figtext(0.05, 0.02, legend_text, fontsize=8, 
                           bbox=dict(facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            file_path = os.path.join(output_dir, 'target_distribution.png')
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                logger.info(f"Saved {file_path} (size: {file_size} bytes)")
                visualization_files.append(file_path)
            else:
                logger.error(f"Failed to create {file_path}")
        else:
            logger.warning("No target data available for visualization")
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}", exc_info=True)
    
    # Verify files were created
    for expected_file in visualization_files:
        if os.path.exists(expected_file):
            file_size = os.path.getsize(expected_file)
            logger.info(f"Verified file {expected_file} exists (size: {file_size} bytes)")
        else:
            logger.error(f"Expected file {expected_file} was not created!")
    
    logger.info(f"Created {len(visualization_files)} visualizations in {output_dir}")
    return visualization_files