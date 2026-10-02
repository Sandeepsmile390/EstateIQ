"""
GenAI Recommendation Engine for Facility Intelligence.
Receives strictly validated ML model outputs and transforms them into operational 7-part structured recommendations.
CRITICAL MANDATE: Never invent measurements, probabilities, sensor values, financial savings, or health claims!
"""

from typing import Dict, Any

class GenAIExplanationEngine:
    """GenAI explanation layer converting structured ML predictions into human-readable action plans."""
    
    def generate_recommendation(self, structured_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives validated ML dictionary:
        {
          "issue": "energy_anomaly",
          "building": "Block B",
          "actual": 120,
          "expected": 85,
          "deviation_percent": 41,
          "important_features": ["occupancy", "temperature", "hvac_load"]
        }
        Returns 7-part structured response.
        """
        issue = structured_input.get("issue", "general_alert")
        building = structured_input.get("building", "Facility Zone")
        actual = structured_input.get("actual", "N/A")
        expected = structured_input.get("expected", "N/A")
        dev_pct = structured_input.get("deviation_percent", 0)
        important_feats = structured_input.get("important_features", [])
        
        # Determine Severity based strictly on deviation percent or input
        if dev_pct > 35:
            severity = "HIGH"
        elif dev_pct > 15:
            severity = "MEDIUM"
        else:
            severity = "LOW"
            
        feats_str = ", ".join(important_feats) if important_feats else "operational usage patterns"
        
        # 1. What happened?
        what_happened = f"Recorded sensor metric in {building} reached {actual} against expected baseline of {expected}."
        
        # 2. What is predicted?
        what_is_predicted = f"Current trend indicates a {dev_pct}% deviation from expected nominal baseline."
        
        # 3. Why was it flagged?
        why_flagged = f"Flagged by anomaly model due to significant variance driven primarily by: {feats_str}."
        
        # 4. Severity
        # severity variable computed above
        
        # 5. Recommended Action
        if "energy" in issue.lower():
            recommended_action = f"Inspect HVAC operational schedules and setback controls in {building}. Check for un-scheduled equipment run."
        elif "water" in issue.lower():
            recommended_action = f"Perform physical check of supply line valves and restrooms in {building}. Verify flow meter integrity."
        elif "waste" in issue.lower():
            recommended_action = f"Dispatch collection crew to clear bin in {building} before overflow threshold is breached."
        elif "equipment" in issue.lower():
            recommended_action = f"Schedule maintenance inspection for equipment in {building} to measure vibration and thermal tolerances."
        else:
            recommended_action = f"Conduct routine facility check in {building} and review telemetry logs."
            
        # 6. Assumptions
        assumptions = "Assumes sensor baseline calibrations are current and historical occupancy patterns reflect standard operation."
        
        # 7. Limitations
        limitations = "Model output is an operational decision-support indicator and does not prove direct physical causation or guarantee savings."
        
        return {
            "title": f"Facility Decision Support Alert: {issue.replace('_', ' ').title()} - {building}",
            "severity": severity,
            "1_what_happened": what_happened,
            "2_what_is_predicted": what_is_predicted,
            "3_why_was_it_flagged": why_flagged,
            "4_severity": severity,
            "5_recommended_action": recommended_action,
            "6_assumptions": assumptions,
            "7_limitations": limitations
        }

if __name__ == "__main__":
    engine = GenAIExplanationEngine()
    test_input = {
        "issue": "energy_anomaly",
        "building": "Block B Hostel",
        "actual": 120,
        "expected": 85,
        "deviation_percent": 41.1,
        "important_features": ["occupancy", "temperature", "hvac_load"]
    }
    rec = engine.generate_recommendation(test_input)
    print("[GenAI Engine Test] Structured 7-Part Recommendation:\n", rec)
