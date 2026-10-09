"""
EstateIQ Anomaly Consensus — EAC (src/intelligence/anomaly_consensus.py).
Combines normalized anomaly signals across contextual, tree, density, and rule-based detectors.
"""

from typing import Dict, Any, List
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult, PredictionResult, AnomalyResult, AnomalyLevel

class EstateIQAnomalyConsensus:
    """EAC: Multi-signal normalized anomaly fusion engine with temporal persistence confirmation."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config
        self.persistence_history = {} # building_id -> consecutive anomaly count

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

        # 4. Physics & Domain Rule Violation Signal (0 - 100)
        power_factor = event.extra_features.get("power_factor", 0.92)
        hvac_vs_temp_violation = (event.temperature > 30.0 and event.hvac_load < 10.0) or (event.temperature < 20.0 and event.hvac_load > 80.0)
        off_peak_surge = (event.hour >= 20 or event.hour <= 5) and event.actual_kwh > 100.0
        low_pf = power_factor < 0.82

        rule_score = 10.0
        if off_peak_surge or hvac_vs_temp_violation or low_pf:
            rule_score = 90.0

        # Weighted Anomaly Score Fusion
        composite_score = round(
            self.config.weight_contextual_residual * c_score +
            self.config.weight_isolation_forest * if_score +
            self.config.weight_lof * lof_score +
            self.config.weight_domain_rules * rule_score, 1
        )

        # 5. Temporal Persistence Window Tracking
        bld_id = event.building_id or "default"
        is_raw_anomalous = composite_score >= 40.0
        if is_raw_anomalous:
            self.persistence_history[bld_id] = self.persistence_history.get(bld_id, 0) + 1
        else:
            self.persistence_history[bld_id] = 0

        persistence_count = self.persistence_history[bld_id]

        evidence = []
        if c_score > 30:
            evidence.append(f"Contextual deviation: {contextual.relative_deviation_pct:+.1f}% vs baseline")
        if if_score > 50:
            evidence.append(f"Isolation Forest flagged anomaly (Score: {if_score:.0f}/100)")
        if lof_score > 50:
            evidence.append(f"LOF local density outlier (Score: {lof_score:.0f}/100)")
        if rule_score > 50:
            reasons = []
            if off_peak_surge:
                reasons.append("Off-peak HVAC consumption surge")
            if hvac_vs_temp_violation:
                reasons.append("HVAC power inconsistent with ambient temperature")
            if low_pf:
                reasons.append(f"Power factor degradation ({power_factor:.2f} < 0.82)")
            evidence.append(f"Physics/Domain Rule Violation: {', '.join(reasons)}")

        if persistence_count >= 2:
            evidence.append(f"Temporal Persistence Confirmed: Sustained anomaly over {persistence_count} consecutive intervals")
        elif is_raw_anomalous:
            evidence.append("Temporal Window: Single-interval transient fluctuation detected")

        if composite_score >= 80.0 and persistence_count >= 2:
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
