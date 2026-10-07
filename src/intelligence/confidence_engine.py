"""
EstateIQ Confidence Intelligence — ECI (src/intelligence/confidence_engine.py).
Calculates transparent deterministic confidence (0-100%) separate from severity.
"""

from typing import Dict, Any
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import QualityResult, AnomalyResult, ConfidenceResult

class EstateIQConfidenceIntelligence:
    """ECI: Multi-source deterministic decision confidence calculator."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def calculate(
        self,
        quality: QualityResult,
        anomaly: AnomalyResult,
        historical_days_available: int = 365
    ) -> ConfidenceResult:
        model_agreement = anomaly.model_agreement_pct
        historical_coverage = min(100.0, (historical_days_available / 365.0) * 100.0)
        feature_completeness = 95.0
        sensor_reliability = quality.sensor_reliability

        confidence = round(
            self.config.weight_data_quality * quality.overall_quality_score +
            self.config.weight_model_agreement * model_agreement +
            self.config.weight_historical_coverage * historical_coverage +
            self.config.weight_feature_completeness * feature_completeness +
            self.config.weight_sensor_reliability * sensor_reliability, 1
        )

        if confidence >= self.config.high_confidence_gate:
            level = "HIGH"
        elif confidence >= self.config.medium_confidence_gate:
            level = "MEDIUM"
        else:
            level = "LOW"

        gate_passed = confidence >= self.config.medium_confidence_gate

        return ConfidenceResult(
            confidence_pct=confidence,
            confidence_level=level,
            gate_passed=gate_passed
        )
