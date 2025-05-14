import os

# Create directories
CACHE_DIR = "cache"
DATA_DIR = "data"
RESULTS_DIR = "results"
FIGURES_DIR = "figures"

# General settings
DEFAULT_DISEASE = "Familial Hypercholesterolemia"

# Ensure all necessary directories exist
for directory in [CACHE_DIR, DATA_DIR, RESULTS_DIR, FIGURES_DIR]:
    os.makedirs(directory, exist_ok=True)

print("Config loaded successfully!")
