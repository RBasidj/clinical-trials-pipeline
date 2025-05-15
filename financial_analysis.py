## File: financial_analysis.py
## Location: Replace the entire file

from datetime import datetime, timedelta
import os
import yfinance as yf
from collections import defaultdict
import pandas as pd
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
import time

OPENAI_AVAILABLE = os.getenv("OPENAI_API_KEY") is not None
CACHE_DIR = "cache/finance"
os.makedirs(CACHE_DIR, exist_ok=True)

# ================================
# Caching Helpers
# ================================

def get_cache_key(prefix, data):
    """Generate a cache key from data"""
    data_str = str(data).lower()
    return f"{prefix}_{hashlib.md5(data_str.encode()).hexdigest()}"

def get_cached_data(key, expiry_days=7):
    """Retrieve cached data if valid"""
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, "r") as f:
            data = json.load(f)
        
        # Check if expired
        timestamp = data.get("timestamp", 0)
        now = time.time()
        expiry_seconds = expiry_days * 86400  # Convert days to seconds
        
        if now - timestamp > expiry_seconds:
            print(f"Cache expired for {key}")
            return None
        
        print(f"Using cached data for {key}")
        return data.get("data")
    except Exception as e:
        print(f"Error reading cache for {key}: {e}")
        return None

def cache_data(key, data):
    """Cache data with timestamp"""
    cache_file = os.path.join(CACHE_DIR, f"{key}.json")
    
    cache_data = {
        "timestamp": time.time(),
        "data": data
    }
    
    try:
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        print(f"Cached data for {key}")
        return True
    except Exception as e:
        print(f"Error caching data for {key}: {e}")
        return False

# ================================
# Stock Lookup Helpers
# ================================

def lookup_stock(ticker):
    """Fetch 1-year performance and market cap for a ticker with caching."""
    if not ticker or ticker.lower() in ['private company', 'unknown', 'n/a']:
        return {"ticker": ticker, "error": "Invalid or unsupported ticker"}
    
    # Check cache first
    cache_key = get_cache_key("stock", ticker)
    cached_data = get_cached_data(cache_key, expiry_days=1)  # Cache for 1 day
    
    if cached_data:
        return cached_data
    
    try:
        stock = yf.Ticker(ticker)
        stock_info = stock.info
        
        # Faster approach - just get today's data and use price change data directly
        market_cap = stock_info.get('marketCap', 'Unknown')
        current_price = stock_info.get('currentPrice', stock_info.get('regularMarketPrice', None))
        price_change_1y = stock_info.get('52WeekChange', None)
        
        # If we couldn't get the data from info, fall back to history
        if current_price is None or price_change_1y is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
            
            if hist.empty:
                raise ValueError("No historical data")
            
            first_price = hist.iloc[0]['Close']
            current_price = hist.iloc[-1]['Close']
            price_change_1y = ((current_price - first_price) / first_price) * 100
        else:
            # Convert to percentage if needed
            if isinstance(price_change_1y, float) and price_change_1y < 1 and price_change_1y > -1:
                price_change_1y *= 100
        
        result = {
            'ticker': ticker,
            'price': current_price,
            'change_1y': price_change_1y,
            'market_cap': market_cap
        }
        
        # Cache the result
        cache_data(cache_key, result)
        
        return result
    except Exception as e:
        error_result = {"ticker": ticker, "error": str(e)}
        # Still cache errors to avoid repeated failures
        cache_data(cache_key, error_result)
        return error_result

def lookup_stocks_parallel(ticker_list, max_workers=20):
    """Run stock lookups in parallel with high concurrency."""
    # Filter out duplicates and invalid tickers
    unique_tickers = list(set([t for t in ticker_list if t and t.lower() not in ['private company', 'unknown', 'n/a']]))
    
    if not unique_tickers:
        return []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks at once
        futures = {executor.submit(lookup_stock, ticker): ticker for ticker in unique_tickers}
        
        # Process results as they complete
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    return results

# ================================
# Company Mapping + Analysis
# ================================

def find_company_for_drug(drug_name):
    """Find company for a drug using OpenAI API with caching"""
    if not OPENAI_AVAILABLE:
        return {"company": "Unknown", "tickers": []}
    
    # Check cache first
    cache_key = get_cache_key("drug_company", drug_name)
    cached_data = get_cached_data(cache_key, expiry_days=30)  # Cache for 30 days
    
    if cached_data:
        return cached_data
    
    try:
        from openai import OpenAI
        import json
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
        What company or companies make or have rights to the drug "{drug_name}"?
        Please return ONLY a JSON object with this structure:
        {{
            "company": "Company Name",
            "tickers": ["TICKER1", "TICKER2"]
        }}
        If you don't know, return {{"company": "Unknown", "tickers": []}}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a biotech financial analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        content = response.choices[0].message.content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            result = json.loads(content[start_idx:end_idx])
            # Cache the result
            cache_data(cache_key, result)
            return result
        
        default_result = {"company": "Unknown", "tickers": []}
        cache_data(cache_key, default_result)
        return default_result
    
    except Exception as e:
        print(f"Error finding company for {drug_name}: {e}")
        default_result = {"company": "Unknown", "tickers": []}
        cache_data(cache_key, default_result)
        return default_result

def get_companies_from_drugs(interventions, skip_financial=False):
    """
    Map interventions to companies and get basic stock information
    """
    # This list is extended based on common drugs in clinical trials
    company_mappings = {
        'alirocumab': {'company': 'Regeneron/Sanofi', 'tickers': ['REGN', 'SNY']},
        'evolocumab': {'company': 'Amgen', 'tickers': ['AMGN']},
        'mipomersen': {'company': 'Ionis Pharmaceuticals', 'tickers': ['IONS']},
        'inclisiran': {'company': 'Novartis', 'tickers': ['NVS']},
        'bempedoic acid': {'company': 'Esperion Therapeutics', 'tickers': ['ESPR']},
        'rosuvastatin': {'company': 'AstraZeneca', 'tickers': ['AZN']},
        'ezetimibe': {'company': 'Merck', 'tickers': ['MRK']},
        'atorvastatin': {'company': 'Pfizer', 'tickers': ['PFE']},
        'simvastatin': {'company': 'Merck', 'tickers': ['MRK']},
        'pembrolizumab': {'company': 'Merck', 'tickers': ['MRK']},
        'nivolumab': {'company': 'Bristol-Myers Squibb', 'tickers': ['BMY']},
        'atezolizumab': {'company': 'Roche', 'tickers': ['RHHBY']},
        'durvalumab': {'company': 'AstraZeneca', 'tickers': ['AZN']},
        'avelumab': {'company': 'Merck KGaA/Pfizer', 'tickers': ['MKKGY', 'PFE']},
        'axicabtagene ciloleucel': {'company': 'Gilead', 'tickers': ['GILD']},
        'tisagenlecleucel': {'company': 'Novartis', 'tickers': ['NVS']}
    }
    
    # Process all interventions in parallel
    def process_intervention(intervention):
        drug_name = intervention.get('name', '').lower()
        
        if 'placebo' in drug_name or 'saline' in drug_name:
            return None
        
        # Check known mappings first (fast)
        for known_drug, info in company_mappings.items():
            if known_drug in drug_name:
                result = {
                    'drug': intervention.get('name'),
                    'modality': intervention.get('modality'),
                    'target': intervention.get('target'),
                    'company': info.get('company'),
                    'tickers': info.get('tickers', []),
                    'stock_performance': [] if skip_financial else None
                }
                return result
        
        # Use OpenAI if needed
        if OPENAI_AVAILABLE:
            company_info = find_company_for_drug(drug_name)
            
            if company_info.get('company') != "Unknown":
                result = {
                    'drug': intervention.get('name'),
                    'modality': intervention.get('modality'),
                    'target': intervention.get('target'),
                    'company': company_info.get('company'),
                    'tickers': company_info.get('tickers', []),
                    'stock_performance': [] if skip_financial else None
                }
                return result
        
        # Default if nothing found
        return {
            'drug': intervention.get('name'),
            'modality': intervention.get('modality'),
            'target': intervention.get('target'),
            'company': "Unknown",
            'tickers': [],
            'stock_performance': []
        }
    
    # Process all interventions in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        intervention_futures = list(executor.map(process_intervention, interventions))
    
    # Filter out None results
    company_analysis = [result for result in intervention_futures if result is not None]
    
    # If financial analysis is skipped, return early
    if skip_financial:
        return company_analysis
    
    # Collect all unique tickers to look up
    all_tickers = []
    for analysis in company_analysis:
        all_tickers.extend(analysis.get('tickers', []))
    
    # Look up all stock info in parallel
    ticker_to_performance = {}
    if all_tickers:
        stock_results = lookup_stocks_parallel(all_tickers)
        
        # Map results back to tickers
        for result in stock_results:
            ticker_to_performance[result.get('ticker')] = result
    
    # Update company analysis with stock performance
    for analysis in company_analysis:
        tickers = analysis.get('tickers', [])
        stock_performance = []
        
        for ticker in tickers:
            if ticker in ticker_to_performance:
                stock_performance.append(ticker_to_performance[ticker])
        
        analysis['stock_performance'] = stock_performance
    
    return company_analysis

## File: financial_analysis.py
## Location: In the analyze_competitive_landscape function, where key_outcome is determined

## File: financial_analysis.py
## Location: Inside the analyze_competitive_landscape function, update the key outcome extraction

def analyze_competitive_landscape(processed_trials, company_analysis):
    """
    Analyze competitive positioning of different drugs and companies
    """
    from collections import defaultdict
    import pandas as pd
    
    # Group trials by target
    target_groups = defaultdict(list)
    
    for drug_info in company_analysis:
        target = drug_info.get('target')
        if target and target != 'unknown':
            target_groups[target].append(drug_info)
    
    competitive_analysis = []
    
    # Analyze each target space
    for target, drugs in target_groups.items():
        if len(drugs) <= 1:  # Skip targets with only one drug
            continue
        
        # Create entry for this competitive space
        competition = {
            'target': target,
            'drugs': len(drugs),
            'companies': set(),
            'comparative_data': []
        }
        
        # Find trials for each drug in this target space
        for drug_info in drugs:
            drug_name = drug_info.get('drug')
            drug_trials = []
            
            for trial in processed_trials:
                for intervention in trial.get('interventions', []):
                    if intervention.get('name') == drug_name:
                        drug_trials.append(trial)
            
            # Company info
            company = drug_info.get('company')
            competition['companies'].add(company)
            
            # Extract key data points
            primary_outcomes = []
            for trial in drug_trials:
                primary_outcomes.extend(trial.get('primary_outcomes', []))
            
            # Enhanced effectiveness metrics extraction
            effectiveness = "No data"
            
            # Define better keywords based on drug/target type
            # This covers more therapeutic areas and outcome measures
            outcome_keywords = [
                'reduction', 'decrease', 'improvement', 'relief', 'healing', 'eradication',
                'resolution', 'response', 'efficacy', 'safety', 'symptom', 'acid', 'ph',
                'gerd', 'heartburn', 'reflux', 'erosive', 'esophagitis', 'ulcer',
                'ldl', 'cholesterol', 'lipid', 'biomarker', 'glucose', 'hba1c',
                'pain', 'score', 'scale', 'assessment', 'endpoint'
            ]
            
            # First check all primary outcomes
            if primary_outcomes:
                # Try to find the best match using keywords
                for outcome in primary_outcomes:
                    if outcome:  # Ensure outcome isn't None
                        outcome_lower = outcome.lower()
                        if any(keyword in outcome_lower for keyword in outcome_keywords):
                            effectiveness = outcome
                            break
                
                # If no good match but we have outcomes, use the first one
                if effectiveness == "No data" and primary_outcomes and primary_outcomes[0]:
                    effectiveness = primary_outcomes[0]
            
            # Add fallback to secondary outcomes if needed
            if effectiveness == "No data" and drug_trials:
                secondary_outcomes = []
                for trial in drug_trials:
                    secondary_outcomes.extend([o for o in trial.get('secondary_outcomes', []) if o])
                
                for outcome in secondary_outcomes:
                    outcome_lower = outcome.lower()
                    if any(keyword in outcome_lower for keyword in outcome_keywords):
                        effectiveness = f"Secondary: {outcome}"
                        break
                
                # If still no data but we have secondary outcomes, use the first
                if effectiveness == "No data" and secondary_outcomes:
                    effectiveness = f"Secondary: {secondary_outcomes[0]}"
            
            # Final fallback to trial phase or status
            if effectiveness == "No data" and drug_trials:
                # For PPI drugs, use a standard outcome
                if "proton pump" in target.lower() or any(ppi in drug_name.lower() for ppi in ["prazole", "nexium", "prilosec", "prevacid", "zegerid"]):
                    effectiveness = "Acid suppression efficacy"
                # Try phase information
                else:
                    for trial in drug_trials:
                        phase = trial.get('phase')
                        if phase and phase != "Not Available":
                            effectiveness = f"Phase {phase} trial"
                            break
                    
                    # Try status if phase didn't work
                    if effectiveness == "No data":
                        for trial in drug_trials:
                            status = trial.get('status')
                            if status:
                                effectiveness = f"Status: {status}"
                                break
            
            # Add to comparative analysis
            competition['comparative_data'].append({
                'drug': drug_name,
                'company': company,
                'modality': drug_info.get('modality'),
                'trials': len(drug_trials),
                'key_outcome': effectiveness,
                'stock_performance': drug_info.get('stock_performance', [])
            })
        
        competitive_analysis.append(competition)
    
    return competitive_analysis

def analyze_clinical_thresholds(processed_trials, disease):
    """
    Analyze what outcome thresholds are clinically and commercially relevant
    """
    if not OPENAI_AVAILABLE:
        return {
            "thresholds": {},
            "outcome_categories": {},
            "threshold_relevance": {
                "summary": "OpenAI API not available for threshold analysis",
                "notes": []
            }
        }
    
    # Check cache for this disease
    cache_key = get_cache_key("thresholds", disease)
    cached_thresholds = get_cached_data(cache_key, expiry_days=30)
    
    if cached_thresholds:
        thresholds = cached_thresholds
    else:
        # Use OpenAI to get benchmark thresholds
        thresholds = get_benchmark_thresholds(disease)
        # Cache the results
        cache_data(cache_key, thresholds)
    
    # Extract outcome measures
    outcome_measures = []
    for trial in processed_trials:
        outcome_measures.extend(trial.get('primary_outcomes', []))
        outcome_measures.extend(trial.get('secondary_outcomes', []))
    
    # Filter outcomes
    biomarker_outcomes = [outcome for outcome in outcome_measures 
                         if isinstance(outcome, str) and any(term in outcome.lower() 
                                                          for term in ['ldl', 'cholesterol', 'lipid', 'biomarker'])]
    
    clinical_outcomes = [outcome for outcome in outcome_measures 
                        if isinstance(outcome, str) and any(term in outcome.lower() 
                                                         for term in ['event', 'death', 'mortality', 'hospitalization'])]
    
    # Summary results
    analysis = {
        "thresholds": thresholds,
        "outcome_categories": {
            "biomarker_outcomes": list(set(biomarker_outcomes)),
            "clinical_outcomes": list(set(clinical_outcomes))
        },
        "threshold_relevance": {
            "summary": "Analysis of how trials in this disease area map to commercial thresholds",
            "notes": []
        }
    }
    
    # Add analytical notes
    if 'biomarker_thresholds' in thresholds:
        for threshold in thresholds.get('biomarker_thresholds', []):
            measure = threshold.get('measure', '').lower()
            relevant_outcomes = [o for o in biomarker_outcomes if measure in o.lower()]
            
            if relevant_outcomes:
                analysis['threshold_relevance']['notes'].append(
                    f"Found {len(relevant_outcomes)} trials measuring {measure}, which requires " +
                    f"{threshold.get('minimum_meaningful')} for clinical relevance and " +
                    f"{threshold.get('competitive_advantage')} for competitive advantage."
                )
    
    return analysis

def get_benchmark_thresholds(disease):
    """Get benchmark thresholds using OpenAI API"""
    try:
        from openai import OpenAI
        import json
        import re
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
        For {disease}, what are the clinically meaningful thresholds for:
        1. Key biomarker changes (e.g., LDL reduction percentage)
        2. Clinical outcome improvements needed for commercial success
        3. What level of improvement would be considered a competitive advantage

        Return a JSON object with this structure:
        {{
            "biomarker_thresholds": [
                {{"measure": "LDL reduction", "minimum_meaningful": "X%", "competitive_advantage": "Y%"}}
            ],
            "clinical_thresholds": [
                {{"outcome": "CV events", "minimum_meaningful": "X% reduction", "competitive_advantage": "Y% reduction"}}
            ],
            "commercial_context": "Brief explanation of what matters for commercial success"
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use 3.5-turbo instead of GPT-4 for speed
            messages=[
                {"role": "system", "content": "You are a biotech investment analyst with deep knowledge of clinical trial endpoints and their commercial implications."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        
        # Find JSON content
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                print("Error parsing JSON from OpenAI response")
        
        return {"error": "Could not extract structured data"}
        
    except Exception as e:
        print(f"Error retrieving benchmark thresholds: {e}")
        return {"error": str(e)}