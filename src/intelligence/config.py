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
    early_exit_zscore_threshold: float = 1.875
    critical_deviation_threshold_pct: float = 25.0
    critical_zscore_threshold: float = 4.0
    after_hours_surge_ratio: float = 1.8
    contextual_threshold_pct: float = 15.0
    min_data_quality_score: float = 40.0
    confidence_gate_threshold_pct: float = 60.0
    epsilon: float = 1e-5

    # Anomaly evidence weights. No model score is inferred unless a fitted
    # detector is explicitly connected to the execution path.
    weight_contextual_residual: float = 0.80
    weight_domain_rules: float = 0.20
    anomaly_score_threshold: float = 55.0
    anomaly_high_threshold: float = 70.0
    anomaly_critical_threshold: float = 85.0
    persistence_max_gap_minutes: float = 60.0
    persistence_max_buildings: int = 10000

    # Decision Engine Weights
    weight_contextual_score: float = 0.20
    weight_anomaly_score: float = 0.30
    weight_forecast_deviation: float = 0.15
    weight_business_impact: float = 0.15
    weight_risk_score: float = 0.10
    weight_opportunity_score: float = 0.10

    # Confidence Engine Weights & Gates
    weight_data_quality: float = 0.25
    weight_model_agreement: float = 0.25  # legacy field name; now evidence support
    weight_historical_coverage: float = 0.20
    weight_feature_completeness: float = 0.15
    weight_sensor_reliability: float = 0.15
    high_confidence_gate: float = 80.0
    medium_confidence_gate: float = 60.0

    def __post_init__(self):
        anomaly_weights = (self.weight_contextual_residual, self.weight_domain_rules)
        if any(weight < 0 for weight in anomaly_weights) or abs(sum(anomaly_weights) - 1.0) > 1e-9:
            raise ValueError("Anomaly evidence weights must be non-negative and sum to 1.0")
        if not (0 <= self.anomaly_score_threshold <= self.anomaly_high_threshold <= self.anomaly_critical_threshold <= 100):
            raise ValueError("Anomaly thresholds must be ordered within [0, 100]")
        if self.epsilon <= 0 or self.persistence_max_gap_minutes <= 0 or self.persistence_max_buildings < 1:
            raise ValueError("epsilon, persistence gap, and persistence capacity must be positive")
        if self.critical_zscore_threshold <= 0 or self.after_hours_surge_ratio <= 1:
            raise ValueError("critical z-score must be positive and after-hours ratio must exceed 1")
        if self.default_tariff_inr_kwh < 0 or self.default_emission_factor_kg_kwh < 0:
            raise ValueError("tariff and emission factors must be non-negative")
        decision_weights = (
            self.weight_contextual_score, self.weight_anomaly_score,
            self.weight_forecast_deviation, self.weight_business_impact,
            self.weight_risk_score, self.weight_opportunity_score,
        )
        if any(weight < 0 for weight in decision_weights) or abs(sum(decision_weights) - 1.0) > 1e-9:
            raise ValueError("Decision weights must be non-negative and sum to 1.0")

DEFAULT_DIF_CONFIG = DIFConfig()
