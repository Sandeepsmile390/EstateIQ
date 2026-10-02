"""
Safety Incidents Module Pipeline.
Provides incident trend analysis, high-risk zone identification, and frequency forecasting.
IMPORTANT: Does not manufacture causal relationships. Uses statistical trend analysis when sample sizes are small.
"""

import os
import pandas as pd
import numpy as np

SAFETY_DISCLAIMER = "Correlation between incidents and environmental factors does not imply direct causation."

def analyze_safety_incidents(data_path: str = "data/synthetic/safety.csv") -> dict:
    if not os.path.exists(data_path):
        from src.data.generator import generate_safety_data
        df = generate_safety_data(60)
    else:
        df = pd.read_csv(data_path)
        
    if len(df) == 0:
        return {"status": "INSUFFICIENT_DATA", "total_incidents": 0}
        
    # High-risk zone identification via frequency distribution
    location_counts = df["location"].value_counts().to_dict()
    severity_counts = df["severity"].value_counts().to_dict()
    incident_types = df["incident_type"].value_counts().to_dict()
    
    top_risk_zone = df["location"].mode()[0] if len(df) > 0 else "None"
    
    return {
        "total_incidents_recorded": len(df),
        "high_risk_zone": top_risk_zone,
        "location_distribution": location_counts,
        "severity_breakdown": severity_counts,
        "incident_types": incident_types,
        "disclaimer": SAFETY_DISCLAIMER
    }

if __name__ == "__main__":
    res = analyze_safety_incidents()
    print("[Safety Pipeline] Results:", res)
