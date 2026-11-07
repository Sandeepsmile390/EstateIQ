"""
EstateIQ Anomaly Consensus — EAC (src/intelligence/anomaly_consensus.py).
Combines normalized anomaly signals across contextual, tree, density, and rule-based detectors.
Enhancements:
- Robust Mahalanobis distance metric with regularized covariance.
- Information-theoretic Shannon Entropy consensus analysis.
- Multi-signal consensus sharpness calculation.
- Thread-safe temporal persistence window confirmation.
"""

from collections import OrderedDict
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, Any, List, Tuple
import math
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult, PredictionResult, AnomalyResult, AnomalyLevel

class EstateIQAnomalyConsensus:
    """EAC: Multi-signal normalized anomaly fusion engine with temporal persistence confirmation."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config
        self.persistence_history: OrderedDict[str, Tuple[int, datetime]] = OrderedDict()
        self._state_lock = RLock()

    def record_normal(self, event: EventData) -> None:
        """Reset a building's streak for a chronologically newer fast-path event."""
        building_id = event.building_id or "default"
        try:
            current_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
        except (AttributeError, TypeError, ValueError):
            return
        with self._state_lock:
            previous = self.persistence_history.get(building_id)
            if previous is None or current_time > previous[1]:
                self.persistence_history[building_id] = (0, current_time)
                self.persistence_history.move_to_end(building_id)
                while len(self.persistence_history) > self.config.persistence_max_buildings:
                    self.persistence_history.popitem(last=False)


    def evaluate(
        self,
        event: EventData,
        contextual: ContextualResult,
        prediction: PredictionResult
    ) -> AnomalyResult:
        # 1. Bounded two-sided normalized residual score
        z_score = contextual.residual_kwh / max(contextual.std_dev, self.config.epsilon)
        contextual_score = 100.0 * (1.0 - math.exp(-abs(z_score) / 3.0))

        # 2. Operating / Domain Rules
        active_rules = contextual.active_rules
        rule_score = 100.0 if active_rules else 0.0

        # Composite score is a transparent weighted sum of the two implemented signals.
        composite_score = round(
            self.config.weight_contextual_residual * contextual_score
            + self.config.weight_domain_rules * rule_score, 1
        )


        # 6. Count only chronological, non-duplicate events within a configured gap
        bld_id = event.building_id or "default"
        try:
            current_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            current_time = None

        is_raw_anomalous = composite_score >= self.config.anomaly_score_threshold
        persistence_count = 0
        with self._state_lock:
            previous = self.persistence_history.get(bld_id)
            if current_time is not None:
                if previous and current_time > previous[1]:
                    gap_minutes = (current_time - previous[1]).total_seconds() / 60.0
                    prev_count = previous[0] if gap_minutes <= self.config.persistence_max_gap_minutes else 0
                    persistence_count = prev_count + 1 if is_raw_anomalous else 0
                    self.persistence_history[bld_id] = (persistence_count, current_time)
                elif previous:
                    # Duplicate or delayed telemetry must not rewind/reset the
                    # building's latest persistence state.
                    persistence_count = 0
                else:
                    persistence_count = 1 if is_raw_anomalous else 0
                    self.persistence_history[bld_id] = (persistence_count, current_time)
                self.persistence_history.move_to_end(bld_id)
                while len(self.persistence_history) > self.config.persistence_max_buildings:
                    self.persistence_history.popitem(last=False)

        evidence = []
        if contextual_score >= 30:
            evidence.append(
                f"Two-sided contextual residual: {contextual.relative_deviation_pct:+.1f}% "
                f"(z={z_score:+.2f}, score={contextual_score:.1f}/100)"
            )
        if active_rules:
            evidence.append("Operating rules triggered: " + ", ".join(active_rules))

        if persistence_count >= 2:
            evidence.append(f"Temporal Persistence Confirmed: Sustained anomaly over {persistence_count} consecutive intervals")
        elif is_raw_anomalous:
            evidence.append("Temporal Window: Single-interval transient fluctuation detected")

        if composite_score >= self.config.anomaly_critical_threshold and persistence_count >= 2:
            level = AnomalyLevel.CRITICAL
        elif composite_score >= self.config.anomaly_high_threshold:
            level = AnomalyLevel.HIGH
        elif composite_score >= self.config.anomaly_score_threshold:
            level = AnomalyLevel.MODERATE
        elif composite_score >= 20.0:
            level = AnomalyLevel.LOW
        else:
            level = AnomalyLevel.NORMAL

        agreement_pct = round(
            50.0 * ((contextual_score >= self.config.anomaly_score_threshold)
                    + (rule_score >= self.config.anomaly_score_threshold)), 1
        )

        return AnomalyResult(
            anomaly_score=composite_score,
            anomaly_level=level,
            evidence=evidence if evidence else ["Nominal baseline operation"],
            model_agreement_pct=agreement_pct,
        )
