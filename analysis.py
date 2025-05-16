from collections import Counter

# prompt engineering?
def generate_qualitative_insights(processed_trials, enriched_interventions):
    """Generate deeper qualitative insights about trends"""
    
    #  trials by start date
    sorted_trials = sorted(
        [t for t in processed_trials if t.get('start_date')],
        key=lambda x: x.get('start_date', '2000-01-01')
    )
    
    #  time-based analysis are divided into periods
    if len(sorted_trials) > 5:
        early_period = sorted_trials[:len(sorted_trials)//2]
        late_period = sorted_trials[len(sorted_trials)//2:]
    else:
        early_period = sorted_trials
        late_period = sorted_trials
    
    # 1. modality trends over time
    modality_insights = []
    early_modalities = []
    late_modalities = []
    
    #  modalities by period extracted here
    for trial in early_period:
        for intervention in trial.get('interventions', []):
            int_name = intervention.get('name')
            if int_name:
                for enriched in enriched_interventions:
#necessary
                    if enriched.get('name') == int_name:
                        early_modalities.append(enriched.get('modality', 'unknown'))
                        break
    
    for trial in late_period:
        for intervention in trial.get('interventions', []):
            int_name = intervention.get('name')
            if int_name:
                for enriched in enriched_interventions:
                    if enriched.get('name') == int_name:
                        late_modalities.append(enriched.get('modality', 'unknown'))
                        break
    
    #  changes in modality distribution are analyzed
    early_counter = Counter(early_modalities)
    late_counter = Counter(late_modalities)
    
    for modality in set(early_modalities + late_modalities):
        early_count = early_counter.get(modality, 0)
        late_count = late_counter.get(modality, 0)
        
        if early_count < late_count:
            modality_insights.append(f"There appears to be an increasing trend in {modality} interventions.")
        elif early_count > late_count:
            modality_insights.append(f"There appears to be a decreasing trend in {modality} interventions.")
    
    # outcome measures can be found directly
    outcome_insights = []
    
    early_primary = []
    late_primary = []
    
    for trial in early_period:
        early_primary.extend(trial.get('primary_outcomes', []))
    
    for trial in late_period:
        late_primary.extend(trial.get('primary_outcomes', []))
    
    #  shifts in outcome measures focus are checked
    early_outcomes = Counter([o.lower() for o in early_primary if o])
    late_outcomes = Counter([o.lower() for o in late_primary if o])
    
    # biomarker shifts vs clinical outcomes (market-relevant)
    biomarker_terms = ['ldl', 'cholesterol', 'lipid', 'marker', 'level']
    clinical_terms = ['event', 'mortality', 'death', 'survival', 'hospitalization', 'cardiovascular']
    
    early_biomarker = sum(count for term, count in early_outcomes.items() 
                         if any(b in term for b in biomarker_terms))
    late_biomarker = sum(count for term, count in late_outcomes.items() 
                        if any(b in term for b in biomarker_terms))
    
    early_clinical = sum(count for term, count in early_outcomes.items() 
                        if any(c in term for c in clinical_terms))
    late_clinical = sum(count for term, count in late_outcomes.items() 
                       if any(c in term for c in clinical_terms))
    
    if early_biomarker < late_biomarker:
        outcome_insights.append("There is an increasing focus on biomarker-based outcomes over time.")
    elif early_biomarker > late_biomarker:
        outcome_insights.append("There is a decreasing focus on biomarker-based outcomes over time.")
    
    if early_clinical < late_clinical:
        outcome_insights.append("There is an increasing focus on clinical outcomes over time.")
    elif early_clinical > late_clinical:
        outcome_insights.append("There is a decreasing focus on clinical outcomes over time.")
    
    # now look for trial design trends
    design_insights = []
    
    #  enrollment changes
    early_enrollment = [int(t.get('enrollment')) for t in early_period 
                       if t.get('enrollment') and str(t.get('enrollment')).isdigit()]
    late_enrollment = [int(t.get('enrollment')) for t in late_period 
                      if t.get('enrollment') and str(t.get('enrollment')).isdigit()]
    
    if early_enrollment and late_enrollment:
        early_avg = sum(early_enrollment) / len(early_enrollment)
        late_avg = sum(late_enrollment) / len(late_enrollment)
        
        if early_avg < late_avg:
            design_insights.append(f"Average trial enrollment has increased over time from {early_avg:.1f} to {late_avg:.1f} participants.")
        elif early_avg > late_avg:
            design_insights.append(f"Average trial enrollment has decreased over time from {early_avg:.1f} to {late_avg:.1f} participants.")
    
    #  duration changes
    early_duration = [int(t.get('duration_days')) for t in early_period 
                     if t.get('duration_days') and str(t.get('duration_days')).isdigit()]
    late_duration = [int(t.get('duration_days')) for t in late_period 
                    if t.get('duration_days') and str(t.get('duration_days')).isdigit()]
    
    if early_duration and late_duration:
        early_avg_dur = sum(early_duration) / len(early_duration)
        late_avg_dur = sum(late_duration) / len(late_duration)
        
        if early_avg_dur < late_avg_dur:
            design_insights.append(f"Average trial duration has increased over time from {early_avg_dur:.1f} to {late_avg_dur:.1f} days.")
        elif early_avg_dur > late_avg_dur:
            design_insights.append(f"Average trial duration has decreased over time from {early_avg_dur:.1f} to {late_avg_dur:.1f} days.")
    
    return {
        "modality_trends": modality_insights,
        #improve modality trends if revising script
        "outcome_trends": outcome_insights,
        "design_trends": design_insights
    }
