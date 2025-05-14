from datetime import datetime, timedelta
import os
import yfinance as yf
from collections import defaultdict
import pandas as pd

OPENAI_AVAILABLE = os.getenv("OPENAI_API_KEY") is not None

def get_companies_from_drugs(interventions):
    """
    Map interventions to companies and get basic stock information
    """
    
    # Known drug-company mappings (expand this with OpenAI or a database)
    company_mappings = {

        'alirocumab': {'company': 'Regeneron/Sanofi', 'tickers': ['REGN', 'SNY']},
        'evolocumab': {'company': 'Amgen', 'tickers': ['AMGN']},
        'mipomersen': {'company': 'Ionis Pharmaceuticals', 'tickers': ['IONS']},
        'inclisiran': {'company': 'Novartis', 'tickers': ['NVS']},
        'bempedoic acid': {'company': 'Esperion Therapeutics', 'tickers': ['ESPR']},
        'rosuvastatin': {'company': 'AstraZeneca', 'tickers': ['AZN']},
        'ezetimibe': {'company': 'Merck', 'tickers': ['MRK']},
    }
    
    # OpenAI function to find company for unknown drugs
    def find_company_for_drug(drug_name):
        from openai import OpenAI
        
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
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a biotech financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            import json
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                try:
                    data = json.loads(json_str)
                    return data
                except:
                    return {"company": "Unknown", "tickers": []}
            
            return {"company": "Unknown", "tickers": []}
            
        except Exception as e:
            print(f"Error finding company: {e}")
            return {"company": "Unknown", "tickers": []}
    
    # Results container
    company_analysis = []
    
    # Process each intervention
    for intervention in interventions:
        drug_name = intervention.get('name', '').lower()
        
        # Skip placebo and other non-drugs
        if 'placebo' in drug_name or 'saline' in drug_name:
            continue
        
        # Find company info
        company_info = None
        
        # Check known mappings
        for known_drug, info in company_mappings.items():
            if known_drug in drug_name:
                company_info = info
                break
        
        # If not found, use OpenAI to find info
        if not company_info and OPENAI_AVAILABLE:
            company_info = find_company_for_drug(drug_name)
        
        if not company_info:
            company_info = {"company": "Unknown", "tickers": []}
        
        # Get stock performance for each ticker
        stock_performance = []
        for ticker in company_info.get('tickers', []):
            try:
                # Get 1-year stock data
                stock = yf.Ticker(ticker)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                hist = stock.history(start=start_date.strftime('%Y-%m-%d'), 
                                     end=end_date.strftime('%Y-%m-%d'))
                
                if not hist.empty:
                    first_price = hist.iloc[0]['Close']
                    last_price = hist.iloc[-1]['Close']
                    
                    percent_change = ((last_price - first_price) / first_price) * 100
                    
                    stock_performance.append({
                        'ticker': ticker,
                        'price': last_price,
                        'change_1y': percent_change,
                        'market_cap': stock.info.get('marketCap', 'Unknown')
                    })
            except Exception as e:
                print(f"Error getting stock data for {ticker}: {e}")
                stock_performance.append({
                    'ticker': ticker,
                    'error': str(e)
                })
        
        # Combine drug and company info
        company_analysis.append({
            'drug': intervention.get('name'),
            'modality': intervention.get('modality'),
            'target': intervention.get('target'),
            'company': company_info.get('company'),
            'tickers': company_info.get('tickers'),
            'stock_performance': stock_performance
        })
    
    return company_analysis

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
            
            # Find effectiveness metrics (looking for LDL reduction, etc.)
            effectiveness = "No data"
            for outcome in primary_outcomes:
                if 'ldl' in outcome.lower() or 'cholesterol' in outcome.lower():
                    effectiveness = outcome
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
    # Use OpenAI to get benchmark thresholds for this disease area
    def get_benchmark_thresholds(disease):
        from openai import OpenAI
        
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
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better analytical capabilities
                messages=[
                    {"role": "system", "content": "You are a biotech investment analyst with deep knowledge of clinical trial endpoints and their commercial implications."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            import json
            import re
            
            # Find JSON content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    data = json.loads(json_str)
                    return data
                except json.JSONDecodeError:
                    print("Error parsing JSON from OpenAI response")
            
            return {"error": "Could not extract structured data"}
            
        except Exception as e:
            print(f"Error retrieving benchmark thresholds: {e}")
            return {"error": str(e)}
    
    # Get benchmark thresholds
    thresholds = get_benchmark_thresholds(disease)
    
    # Extract all outcome measures from trials
    outcome_measures = []
    for trial in processed_trials:
        outcome_measures.extend(trial.get('primary_outcomes', []))
        outcome_measures.extend(trial.get('secondary_outcomes', []))
    
    # Categorize outcomes
    biomarker_outcomes = [outcome for outcome in outcome_measures 
                         if any(term in outcome.lower() for term in 
                               ['ldl', 'cholesterol', 'lipid', 'biomarker'])]
    
    clinical_outcomes = [outcome for outcome in outcome_measures 
                        if any(term in outcome.lower() for term in 
                              ['event', 'death', 'mortality', 'hospitalization'])]
    
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
        for threshold in thresholds['biomarker_thresholds']:
            measure = threshold.get('measure', '').lower()
            relevant_outcomes = [o for o in biomarker_outcomes if measure in o.lower()]
            
            if relevant_outcomes:
                analysis['threshold_relevance']['notes'].append(
                    f"Found {len(relevant_outcomes)} trials measuring {measure}, which requires " +
                    f"{threshold.get('minimum_meaningful')} for clinical relevance and " +
                    f"{threshold.get('competitive_advantage')} for competitive advantage."
                )
    
    return analysis