"""
Evaluation Metrics & Reference Baselines (elite_algo/metrics.py).
Implements standard statistical metrics for forecasting models, classification metrics for anomaly detection,
reference baseline models, and Decision Layer evaluation criteria.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve

class ForecastingMetrics:
    """Calculates time-series forecasting regression metrics."""

    @staticmethod
    def calculate_all(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        if len(y_true) == 0 or len(y_pred) == 0:
            return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "mape": 0.0, "max_error": 0.0}

        mae = float(mean_absolute_error(y_true, y_pred))
        mse = float(mean_squared_error(y_true, y_pred))
        rmse = float(np.sqrt(mse))
        r2 = float(r2_score(y_true, y_pred))

        # Safe MAPE calculation avoiding zero division
        non_zero_mask = y_true != 0
        if np.any(non_zero_mask):
            mape = float(np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100.0)
        else:
            mape = 0.0

        max_err = float(np.max(np.abs(y_true - y_pred)))

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "mape": round(mape, 2),
            "max_error": round(max_err, 4)
        }

class BaselineModels:
    """Reference baseline models for scientific comparison."""

    @staticmethod
    def naive_persistence(train_series: np.ndarray, test_series: np.ndarray) -> np.ndarray:
        """Naive Persistence: Predicts y_t = y_{t-1}."""
        if len(train_series) == 0 or len(test_series) == 0:
            return np.zeros_like(test_series)
        preds = np.zeros_like(test_series)
        preds[0] = train_series[-1]
        preds[1:] = test_series[:-1]
        return preds

    @staticmethod
    def historical_mean(train_series: np.ndarray, test_series: np.ndarray) -> np.ndarray:
        """Historical Mean: Predicts y_t = mean(y_train)."""
        if len(train_series) == 0:
            mean_val = 0.0
        else:
            mean_val = float(np.mean(train_series))
        return np.full_like(test_series, fill_value=mean_val)

class ClassificationMetrics:
    """Calculates classification metrics for anomaly detection where labeled ground truth exists."""

    @staticmethod
    def calculate_all(y_true: np.ndarray, y_pred: np.ndarray, y_scores: Optional[np.ndarray] = None) -> Dict[str, Any]:
        y_true = np.asarray(y_true, dtype=int)
        y_pred = np.asarray(y_pred, dtype=int)

        if len(y_true) == 0:
            return {"status": "NOT EVALUATED", "reason": "Empty dataset"}

        # Check if ground truth contains anomaly variability
        unique_classes = np.unique(y_true)
        if len(unique_classes) < 2:
            return {
                "status": "EVALUATED_SINGLE_CLASS",
                "accuracy": float(np.mean(y_true == y_pred)),
                "precision": "NOT EVALUATED (Single class in ground truth)",
                "recall": "NOT EVALUATED (Single class in ground truth)",
                "f1_score": "NOT EVALUATED",
                "roc_auc": "NOT EVALUATED"
            }

        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))

        auc_score = "NOT EVALUATED"
        if y_scores is not None and len(np.unique(y_true)) > 1:
            try:
                auc_score = round(float(roc_auc_score(y_true, y_scores)), 4)
            except Exception:
                auc_score = "NOT EVALUATED"

        return {
            "status": "EVALUATED",
            "confusion_matrix": {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)},
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": auc_score
        }

class DecisionLayerMetrics:
    """Metrics specifically evaluating the Elite Algorithm Decision Intelligence Layer."""

    @staticmethod
    def evaluate_decision_layer(decision_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not decision_records:
            return {"status": "NOT EVALUATED", "reason": "No decision records provided"}

        total_decisions = len(decision_records)
        agreements = [r.get("model_agreement_pct", 85.0) for r in decision_records]
        false_alert_suppressions = [r for r in decision_records if r.get("suppressed_by_safety_gate", False)]
        priorities = [r.get("priority", "P3_ROUTINE") for r in decision_records]
        cost_savings = [r.get("hourly_cost_inr", 0.0) for r in decision_records]
        confidence_pcts = [r.get("confidence_percent", 90.0) for r in decision_records]

        mean_agreement = float(np.mean(agreements))
        false_alert_rate = float(len(false_alert_suppressions) / total_decisions * 100.0)
        avg_confidence = float(np.mean(confidence_pcts))
        total_potential_savings_inr = float(np.sum(cost_savings))

        # Prioritization distribution
        p1_count = len([p for p in priorities if "P1" in p])
        p2_count = len([p for p in priorities if "P2" in p])
        p3_count = len([p for p in priorities if "P3" in p or "NORMAL" in p])

        return {
            "status": "EVALUATED",
            "total_decisions_evaluated": total_decisions,
            "mean_model_agreement_pct": round(mean_agreement, 2),
            "false_alert_suppression_rate_pct": round(false_alert_rate, 2),
            "avg_confidence_level_pct": round(avg_confidence, 2),
            "total_identified_cost_surge_inr": round(total_potential_savings_inr, 2),
            "priority_distribution": {
                "P1_CRITICAL": p1_count,
                "P2_HIGH": p2_count,
                "P3_ROUTINE": p3_count
            }
        }
