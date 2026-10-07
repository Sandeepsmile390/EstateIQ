"""
EstateIQ Contextual Baseline Engine (src/intelligence/contextual_baseline.py).
Computes expected facility consumption using thermal sensitivity, occupancy,
schedule, and historical fingerprints. Replaces static global thresholds with dynamic adaptive bounds.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from src.intelligence.facility_fingerprint import FacilityFingerprintEngine

class ContextualBaselineEngine:
    """Computes physics & schedule informed contextual baselines and dynamic thresholds."""
    
    def __init__(self):
        self.fingerprint_engine = FacilityFingerprintEngine()

    def compute_expected_baseline(
        self,
        building_id: str,
        hour: int,
        day_of_week: int,
        month: int = 10,
        occupancy: int = 140,
        temperature: float = 31.5,
        hvac_load: float = 75.0,
        operating_schedule: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates expected contextual baseline & dynamic upper/lower normal bounds."""
        prof = self.fingerprint_engine.get_fingerprint(building_id)
        
        base_kw = prof.get("base_kw", 45.0)
        temp_sens = prof.get("temp_sensitivity", 1.85)
        occ_sens = prof.get("occupancy_sensitivity", 0.22)
        
        # Schedule modifier
        is_peak_hour = hour in prof.get("peak_hours", [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        is_weekend = day_of_week in [5, 6]
        
        sched_mult = prof.get("peak_multiplier", 1.35) if is_peak_hour else prof.get("offpeak_multiplier", 0.70)
        if is_weekend:
            sched_mult *= 0.70

        temp_delta = max(0.0, temperature - 22.0)
        
        expected_kwh = (
            base_kw +
            (temp_delta * temp_sens) +
            (occupancy * occ_sens) +
            (hvac_load * 0.45)
        ) * sched_mult

        expected_kwh = round(float(expected_kwh), 2)

        # Dynamic Adaptive Normal Bounds (±20% or ±15 kWh variance)
        normal_std = max(12.0, expected_kwh * 0.18)
        lower_bound = round(max(5.0, expected_kwh - (1.96 * normal_std)), 2)
        upper_bound = round(expected_kwh + (1.96 * normal_std), 2)

        return {
            "building_id": building_id,
            "hour": hour,
            "day_of_week": day_of_week,
            "expected_kwh": expected_kwh,
            "normal_lower_bound": lower_bound,
            "normal_upper_bound": upper_bound,
            "normal_std_dev": round(normal_std, 2),
            "building_type": prof.get("type", "Residential"),
            "schedule_mult": round(sched_mult, 2),
            "provenance": "CONTEXTUAL_BASELINE"
        }

    def evaluate_telemetry_deviation(
        self,
        actual_kwh: float,
        baseline_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluates telemetry against contextual baseline and returns deviation metrics."""
        expected = baseline_info["expected_kwh"]
        abs_dev = round(actual_kwh - expected, 2)
        pct_dev = round((abs_dev / max(expected, 1.0)) * 100.0, 1)
        
        # Z-score normalized deviation
        std_dev = baseline_info.get("normal_std_dev", 15.0)
        z_score = round(abs_dev / max(std_dev, 1.0), 2)
        
        is_anomalous = actual_kwh > baseline_info["normal_upper_bound"] or z_score >= 2.0

        return {
            "actual_kwh": round(actual_kwh, 2),
            "expected_kwh": expected,
            "absolute_deviation_kwh": abs_dev,
            "percentage_deviation_pct": pct_dev,
            "z_score_deviation": z_score,
            "is_contextual_anomaly": is_anomalous,
            "lower_bound": baseline_info["normal_lower_bound"],
            "upper_bound": baseline_info["normal_upper_bound"]
        }
