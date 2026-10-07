"""
EstateIQ Model Consensus Engine (src/intelligence/model_consensus.py).
Evaluates output signals across multiple specialized model engines (XGBoost, Prophet,
IsolationForest, LOF, Contextual Baseline). Calculates Model Consensus Score (0-1)
and Model Disagreement Score (0-1) as explicit intelligence evidence.
"""

import numpy as np
from typing import Dict, Any, List, Optional

class ModelConsensusEngine:
    """Evaluates agreement/disagreement across candidate specialized model signals."""
    
    def evaluate_consensus(
        self,
        xgboost_anomaly_prob: float = 0.85,
        isolation_forest_score: float = 0.88,
        prophet_anomaly_flag: bool = True,
        contextual_anomaly_flag: bool = True,
        lof_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculates consensus ratio and disagreement metric."""
        
        signals = {
            "XGBoost Regressor": 1.0 if xgboost_anomaly_prob >= 0.70 else 0.0,
            "Isolation Forest": 1.0 if isolation_forest_score >= 0.70 else 0.0,
            "Prophet Time-Series": 1.0 if prophet_anomaly_flag else 0.0,
            "Contextual Baseline": 1.0 if contextual_anomaly_flag else 0.0
        }
        
        if lof_score is not None:
            signals["Local Outlier Factor (LOF)"] = 1.0 if lof_score >= 0.70 else 0.0

        votes = list(signals.values())
        mean_vote = float(np.mean(votes))
        
        # Consensus score is max agreement ratio (0.5 = complete split, 1.0 = total agreement)
        consensus_score = round(max(mean_vote, 1.0 - mean_vote), 2)
        
        # Disagreement score: 0.0 when 100% agree, 1.0 when 50/50 split
        disagreement_score = round(1.0 - (abs(mean_vote - 0.5) * 2.0), 2)
        
        majority_anomaly = mean_vote >= 0.5
        
        status_text = (
            "STRONG_CONSENSUS" if consensus_score >= 0.85 else
            ("MODERATE_CONSENSUS" if consensus_score >= 0.65 else "HIGH_DISAGREEMENT")
        )

        explanation = f"{int(sum(votes))} of {len(votes)} analytical model engines flag anomaly behavior."
        if disagreement_score > 0.4:
            explanation += " Model disagreement detected. Downstream confidence score reduced."

        return {
            "model_consensus_score": consensus_score,
            "model_disagreement_score": disagreement_score,
            "majority_anomaly_flag": majority_anomaly,
            "models_evaluated_count": len(votes),
            "anomaly_votes_count": int(sum(votes)),
            "model_signals": signals,
            "consensus_status": status_text,
            "consensus_explanation": explanation,
            "provenance": "MODEL_CONSENSUS_ENGINE"
        }
