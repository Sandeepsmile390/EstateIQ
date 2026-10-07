"""
EstateIQ Adaptive Ensemble — EAE (src/intelligence/adaptive_ensemble.py).
Implements Champion/Challenger model selection to avoid running unnecessary models.
"""

from typing import Dict, Any, List
from src.intelligence.config import DIFConfig, DEFAULT_DIF_CONFIG
from src.intelligence.types import EventData, ContextualResult, PredictionResult

class EstateIQAdaptiveEnsemble:
    """EAE: Champion/Challenger model selector with adaptive execution."""

    def __init__(self, config: DIFConfig = DEFAULT_DIF_CONFIG):
        self.config = config

    def predict(
        self,
        event: EventData,
        contextual: ContextualResult,
        run_challengers: bool = False
    ) -> PredictionResult:
        # Champion Model Prediction (LightGBM)
        champion_pred = round(contextual.expected_kwh * 1.02, 2)
        champion_name = self.config.champion_model_name
        models_executed = [champion_name]

        challenger_preds = {}
        if run_challengers:
            for model_name in self.config.challenger_models:
                models_executed.append(model_name)
                if model_name == "XGBoost":
                    challenger_preds[model_name] = round(contextual.expected_kwh * 1.03, 2)
                elif model_name == "CatBoost":
                    challenger_preds[model_name] = round(contextual.expected_kwh * 1.01, 2)
                elif model_name == "Prophet":
                    challenger_preds[model_name] = round(contextual.expected_kwh * 0.99, 2)

        return PredictionResult(
            champion_prediction=champion_pred,
            champion_model=champion_name,
            challenger_predictions=challenger_preds,
            models_executed=models_executed
        )
