"""
EstateIQ Context Filter — ECF (src/intelligence/context_filter.py).
Fast first-stage contextual screening layer providing dynamic baseline checks and early exit.
"""

from typing import Dict, Any
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult

class EstateIQContextFilter:
    """ECF: Computes contextual expected baseline and relative deviation for early exit."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def evaluate(self, event: EventData) -> ContextualResult:
        # Calculate dynamic expected consumption based on contextual features
        base_hvac = 35.0 if 8 <= event.hour <= 18 else 15.0
        occ_factor = (event.occupancy / 100.0) * 12.0
        temp_factor = max(0.0, (event.temperature - 24.0) * 2.5)

        expected_kwh = round(45.0 + base_hvac + occ_factor + temp_factor, 2)
        std_dev = round(expected_kwh * 0.08, 2)

        residual = round(event.actual_kwh - expected_kwh, 2)
        relative_deviation_pct = round(
            (residual / max(abs(expected_kwh), self.config.epsilon)) * 100.0, 1
        )

        # Contextual score (0 to 100)
        contextual_score = min(100.0, max(0.0, abs(relative_deviation_pct) * 2.0))

        # Check early exit condition: within threshold and no domain rule triggered
        early_exit = abs(relative_deviation_pct) < self.config.contextual_threshold_pct
        reason = "Deviation within normal contextual bound (<10%)" if early_exit else "Significant contextual deviation detected"

        return ContextualResult(
            expected_kwh=expected_kwh,
            std_dev=std_dev,
            residual_kwh=residual,
            relative_deviation_pct=relative_deviation_pct,
            contextual_score=round(contextual_score, 1),
            early_exit=early_exit,
            early_exit_reason=reason
        )
