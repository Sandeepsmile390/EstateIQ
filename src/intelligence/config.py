"""
EstateIQ-DIF Configuration Module (src/intelligence/config.py).
Defines configuration settings, default thresholds, weights, and parameters for EstateIQ-DIF.
"""

from dataclasses import dataclass

@dataclass
class DIFConfig:
    """Configuration settings for EstateIQ-DIF Dynamic Intelligence Engine."""
    default_tariff_inr_kwh: float = 9.50
    default_emission_factor_kg_kwh: float = 0.82
    early_exit_zscore_threshold: float = 1.0
    critical_deviation_threshold_pct: float = 25.0
    contextual_threshold_pct: float = 15.0
    min_data_quality_score: float = 40.0
    confidence_gate_threshold_pct: float = 60.0
    epsilon: float = 1e-5

    # Anomaly Consensus Weights
    weight_contextual_residual: float = 0.35
    weight_isolation_forest: float = 0.25
    weight_lof: float = 0.20
    weight_domain_rules: float = 0.20

    # Decision Engine Weights
    weight_contextual_score: float = 0.20
    weight_anomaly_score: float = 0.30
    weight_forecast_deviation: float = 0.15
    weight_business_impact: float = 0.15
    weight_risk_score: float = 0.10
    weight_opportunity_score: float = 0.10

    # Confidence Engine Weights & Gates
    weight_data_quality: float = 0.25
    weight_model_agreement: float = 0.25
    weight_historical_coverage: float = 0.20
    weight_feature_completeness: float = 0.15
    weight_sensor_reliability: float = 0.15
    high_confidence_gate: float = 80.0
    medium_confidence_gate: float = 60.0

DEFAULT_DIF_CONFIG = DIFConfig()
