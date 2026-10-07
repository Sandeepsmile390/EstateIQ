"""
EstateIQ-DIF Configuration Module (src/intelligence/config.py).
Centralized configuration for thresholds, weights, tariffs, emission factors, and execution policies.
No magic numbers in business logic.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class DIFConfig:
    """Centralized configuration parameters for EstateIQ-DIF."""

    # ECF — Context Filter Thresholds
    contextual_threshold_pct: float = 10.0  # Deviation below 10% triggers early exit
    epsilon: float = 1e-6

    # EAE — Adaptive Ensemble Weights
    champion_model_name: str = "LightGBM"
    challenger_models: list = field(default_factory=lambda: ["XGBoost", "CatBoost", "Prophet"])
    low_confidence_threshold_pct: float = 75.0

    # EAC — Anomaly Consensus Weights
    weight_contextual_residual: float = 0.35
    weight_isolation_forest: float = 0.30
    weight_lof: float = 0.15
    weight_domain_rules: float = 0.20

    # ECI — Confidence Intelligence Weights
    weight_data_quality: float = 0.25
    weight_model_agreement: float = 0.30
    weight_historical_coverage: float = 0.15
    weight_feature_completeness: float = 0.15
    weight_sensor_reliability: float = 0.15

    # Confidence Decision Gates
    high_confidence_gate: float = 80.0
    medium_confidence_gate: float = 50.0

    # EBI — Business Impact Parameters
    default_tariff_inr_kwh: float = 9.50
    default_emission_factor_kg_kwh: float = 0.82
    annualization_factor_days: int = 365

    # EDI — Decision Score Weights
    weight_contextual_score: float = 0.20
    weight_anomaly_score: float = 0.25
    weight_forecast_deviation: float = 0.15
    weight_business_impact: float = 0.15
    weight_risk_score: float = 0.15
    weight_opportunity_score: float = 0.10

    # Selective SHAP Thresholds
    shap_z_score_threshold: float = 2.0
    shap_top_k: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

# Global Default Instance
DEFAULT_DIF_CONFIG = DIFConfig()
