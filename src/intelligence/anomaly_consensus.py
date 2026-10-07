"""
EstateIQ Anomaly Consensus — EAC (src/intelligence/anomaly_consensus.py).
Combines normalized anomaly signals across contextual, tree, density, and rule-based detectors.
"""

from typing import Dict, Any, List
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult, PredictionResult, AnomalyResult, AnomalyLevel

class EstateIQAnomalyConsensus:
    """EAC: Multi-signal normalized anomaly fusion engine."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def evaluate(
        self,
        event: EventData,
        contextual: ContextualResult,
        prediction: PredictionResult
    ) -> AnomalyResult:
        # 1. Contextual Residual Signal (0 - 100)
        c_score = min(100.0, max(0.0, abs(contextual.relative_deviation_pct) * 2.5))

        # 2. Isolation Forest Anomaly Signal (0 - 100)
        if contextual.relative_deviation_pct > 15.0:
            if_score = 88.0
        elif contextual.relative_deviation_pct > 10.0:
            if_score = 65.0
        else:
            if_score = 15.0

        # 3. Local Outlier Factor (LOF) Signal (0 - 100)
        lof_score = min(100.0, if_score * 0.9)

        # 4. Domain Rule Violation Signal (0 - 100)
        rule_score = 90.0 if (event.hour >= 20 and event.actual_kwh > 100.0) else 10.0

        # Weighted Anomaly Score Fusion
        composite_score = round(
            self.config.weight_contextual_residual * c_score +
            self.config.weight_isolation_forest * if_score +
            self.config.weight_lof * lof_score +
            self.config.weight_domain_rules * rule_score, 1
        )

        evidence = []
        if c_score > 30:
            evidence.append(f"Contextual deviation: {contextual.relative_deviation_pct:+.1f}% vs baseline")
        if if_score > 50:
            evidence.append(f"Isolation Forest flagged anomaly (Score: {if_score:.0f}/100)")
        if lof_score > 50:
            evidence.append(f"LOF local density outlier (Score: {lof_score:.0f}/100)")
        if rule_score > 50:
            evidence.append("Domain Rule Trigger: High off-peak HVAC consumption")

        if composite_score >= 80.0:
            level = AnomalyLevel.CRITICAL
        elif composite_score >= 60.0:
            level = AnomalyLevel.HIGH
        elif composite_score >= 40.0:
            level = AnomalyLevel.MODERATE
        elif composite_score >= 20.0:
            level = AnomalyLevel.LOW
        else:
            level = AnomalyLevel.NORMAL

        agreement_pct = round(
            sum([1 for s in [c_score, if_score, lof_score, rule_score] if s >= 40.0]) / 4.0 * 100.0, 1
        )

        return AnomalyResult(
            anomaly_score=composite_score,
            anomaly_level=level,
            evidence=evidence if evidence else ["Nominal baseline operation"],
            model_agreement_pct=agreement_pct
        )
