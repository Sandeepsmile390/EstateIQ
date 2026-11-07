"""
EstateIQ Context Filter — ECF (src/intelligence/context_filter.py).
Fast first-stage contextual screening layer providing dynamic baseline checks and early exit.
"""

from typing import Dict, Any, Optional
from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult
from src.intelligence.domain_rules import evaluate_domain_rules

class EstateIQContextFilter:
    """ECF: Computes contextual expected baseline and relative deviation for early exit."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def evaluate(self, event: EventData,
                 baseline_model: Optional[SeasonalBaselineModel] = None) -> ContextualResult:
        # Prefer a pre-fitted building/slot profile; keep the transparent formula as
        # an explicit cold-start fallback when no historical artifact is supplied.
        estimate = baseline_model.predict(event.building_id, event.timestamp) if baseline_model else None
        if estimate is not None:
            expected_kwh = round(estimate.expected_kwh, 3)
            std_dev = round(estimate.scale_kwh, 3)
            baseline_source = estimate.source
            baseline_observations = estimate.observations
        else:
            base_hvac = 35.0 if 8 <= event.hour <= 18 else 15.0
            occ_factor = (event.occupancy / 100.0) * 12.0
            temp_factor = max(0.0, (event.temperature - 24.0) * 2.5)
            expected_kwh = round(45.0 + base_hvac + occ_factor + temp_factor, 2)
            std_dev = max(expected_kwh * 0.08, self.config.epsilon)
            baseline_source = "HEURISTIC_COLD_START"
            baseline_observations = 0

        residual = round(event.actual_kwh - expected_kwh, 2)
        relative_deviation_pct = round(
            (residual / max(abs(expected_kwh), self.config.epsilon)) * 100.0, 1
        )

        # Contextual score (0 to 100)
        contextual_score = min(100.0, max(0.0, abs(relative_deviation_pct) * 2.0))

        # Check early exit condition: within threshold and no domain rule triggered
        z_score = residual / max(std_dev, self.config.epsilon)
        rules = evaluate_domain_rules(
            event, expected_kwh,
            after_hours_surge_ratio=self.config.after_hours_surge_ratio,
        )
        has_rule_violation = rules["has_violation"]
        early_exit = (
            abs(relative_deviation_pct) < self.config.contextual_threshold_pct
            and abs(z_score) < self.config.early_exit_zscore_threshold
            and not has_rule_violation
        )
        if has_rule_violation:
            reason = "Contextual fast path disabled: an operating-rule violation was detected"
        elif early_exit:
            reason = "Residual is within configured contextual and standardized bounds"
        else:
            reason = "Significant contextual deviation detected"

        return ContextualResult(
            expected_kwh=expected_kwh,
            std_dev=std_dev,
            residual_kwh=residual,
            relative_deviation_pct=relative_deviation_pct,
            contextual_score=round(contextual_score, 1),
            early_exit=early_exit,
            early_exit_reason=reason,
            baseline_source=baseline_source,
            baseline_observations=baseline_observations,
            active_rules=rules["active_rules"]
        )
