"""
Contextual Energy Baseline Engine (src/models/baseline.py).
Establishes physics-aware contextual baselines predicting expected building energy consumption
based on time of day, occupancy, outdoor ambient temperature, and thermal HVAC load.
Calculates operational residual: residual = actual - expected.
Includes NaiveMeanRegressor and MajorityClassClassifier for pipeline evaluation.
"""

import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class ContextualBaselineEngine:
    def __init__(self):
        # Baseline coefficients derived from campus historical telemetry
        self.base_kwh = 45.0
        self.temp_coeff = 1.85     # kWh increase per °C above 22°C
        self.occupancy_coeff = 0.22 # kWh per occupant
        self.hvac_coeff = 0.75     # kWh per % HVAC load

    def calculate_expected_kwh(
        self,
        building_id: str,
        hour: int,
        day_of_week: int,
        occupancy: int = 100,
        temperature: float = 28.0,
        hvac_load: float = 40.0
    ) -> float:
        """Calculates contextual baseline expectation."""
        # Hour of day schedule modifier
        is_operating_hours = 8 <= hour <= 18
        schedule_mult = 1.25 if is_operating_hours else 0.70
        is_weekend = day_of_week in [5, 6]
        if is_weekend:
            schedule_mult *= 0.65

        temp_delta = max(0.0, temperature - 22.0)
        expected = (
            self.base_kwh +
            (temp_delta * self.temp_coeff) +
            (occupancy * self.occupancy_coeff) +
            (hvac_load * self.hvac_coeff)
        ) * schedule_mult

        return round(float(expected), 2)

    def evaluate_deviation(
        self,
        actual_kwh: float,
        expected_kwh: float
    ) -> Dict[str, Any]:
        """Calculates operational residual and baseline deviation percentage."""
        residual = actual_kwh - expected_kwh
        deviation_pct = (residual / max(expected_kwh, 1.0)) * 100.0
        
        is_anomalous = deviation_pct > 30.0 or residual > 35.0

        return {
            "actual_kwh": round(actual_kwh, 2),
            "expected_kwh": round(expected_kwh, 2),
            "residual_kwh": round(residual, 2),
            "deviation_percent": round(deviation_pct, 1),
            "is_anomalous": is_anomalous,
            "disclaimer": "Contextual baseline model derived from historical thermal & schedule profile.",
            "provenance": "DERIVED"
        }

# --- Naive Baseline Models for ML Pipeline Evaluation ---
class NaiveMeanRegressor:
    """Baseline regressor predicting historical mean."""
    def fit(self, X, y):
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X):
        return np.full(len(X), self.mean_)

class MajorityClassClassifier:
    """Baseline classifier predicting majority class."""
    def fit(self, X, y):
        vals, counts = np.unique(y, return_counts=True)
        self.majority_ = vals[np.argmax(counts)]
        return self

    def predict(self, X):
        return np.full(len(X), self.majority_)

    def predict_proba(self, X):
        probs = np.zeros((len(X), 2))
        if self.majority_ == 1:
            probs[:, 1] = 1.0
        else:
            probs[:, 0] = 1.0
        return probs
