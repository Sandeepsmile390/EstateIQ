"""Single-baseline prediction adapter used by EstateIQ-DIF.

This adapter deliberately does not simulate uninstalled challenger models. A
fitted seasonal baseline may be supplied through the contextual stage; otherwise
the contextual value is an explicitly heuristic cold-start estimate.
"""

from typing import Dict
from src.intelligence.config import DIFConfig
from src.intelligence.types import EventData, ContextualResult, PredictionResult


class EstateIQAdaptiveEnsemble:
    """Compatibility adapter; no ensemble is claimed or run."""

    def __init__(self, config: DIFConfig):
        self.config = config

    def predict(self, event: EventData, contextual: ContextualResult,
                run_challengers: bool = False) -> PredictionResult:
        prediction = round(max(0.0, contextual.expected_kwh), 2)
        return PredictionResult(
            champion_prediction=prediction,
            champion_model=contextual.baseline_source,
            challenger_predictions={},
            models_executed=[contextual.baseline_source],
            ensemble_prediction=prediction,
            model_weights={contextual.baseline_source: 1.0},
            model_metrics={},
            epistemic_uncertainty=0.0,
            aleatoric_uncertainty=0.0,
            prediction_interval_lower=0.0,
            prediction_interval_upper=0.0,
            online_regret_bound=0.0,
        )
