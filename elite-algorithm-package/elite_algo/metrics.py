"""
Evaluation Metrics & Reference Baselines (elite_algo/metrics.py).
Implements standard statistical metrics for forecasting models, classification metrics for anomaly detection,
reference baseline models, and Decision Layer evaluation criteria.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional, List

class ForecastingMetrics:
    """Calculates time-series forecasting regression metrics."""

    @staticmethod
    def calculate_all(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)

        if y_true.shape != y_pred.shape:
            raise ValueError("y_true and y_pred must have the same shape")
        finite = np.isfinite(y_true) & np.isfinite(y_pred)
        y_true, y_pred = y_true[finite], y_pred[finite]
        if len(y_true) == 0:
            return {"mae": 0.0, "rmse": 0.0, "r2": 0.0, "mape": 0.0, "max_error": 0.0, "sample_count": 0}

        errors = y_true - y_pred
        mae = float(np.mean(np.abs(errors)))
        mse = float(np.mean(np.square(errors)))
        rmse = float(np.sqrt(mse))
        total = float(np.sum(np.square(y_true - np.mean(y_true))))
        r2 = float(1.0 - np.sum(np.square(errors)) / total) if total > 0 else 0.0

        # Safe MAPE calculation avoiding zero division
        non_zero_mask = y_true != 0
        if np.any(non_zero_mask):
            mape = float(np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100.0)
        else:
            mape = 0.0

        max_err = float(np.max(np.abs(errors)))

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "mape": round(mape, 2),
            "max_error": round(max_err, 4),
            "sample_count": int(len(y_true))
        }

class BaselineModels:
    """Reference baseline models for scientific comparison."""

    @staticmethod
    def naive_persistence(train_series: np.ndarray, test_series: np.ndarray) -> np.ndarray:
        """One-step rolling persistence; each test point uses the prior observed point."""
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

        if y_true.shape != y_pred.shape:
            raise ValueError("y_true and y_pred must have the same shape")
        if y_scores is not None:
            y_scores = np.asarray(y_scores, dtype=float)
            if y_scores.shape != y_true.shape:
                raise ValueError("y_scores must have the same shape as y_true")
            finite = np.isfinite(y_scores)
            y_true, y_pred, y_scores = y_true[finite], y_pred[finite], y_scores[finite]

        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (2 * precision * recall / (precision + recall)
              if recall is not None and precision + recall else 0.0)
        roc_auc = None
        average_precision = None
        if y_scores is not None and np.any(y_true == 1) and np.any(y_true == 0):
            # Mann–Whitney rank statistic (average ranks handle ties).
            order = np.argsort(y_scores, kind="mergesort")
            sorted_scores = y_scores[order]
            ranks = np.empty(len(y_scores), dtype=float)
            first = 0
            while first < len(order):
                last = first + 1
                while last < len(order) and sorted_scores[last] == sorted_scores[first]:
                    last += 1
                ranks[order[first:last]] = (first + 1 + last) / 2.0
                first = last
            positives = int(np.sum(y_true == 1))
            negatives = int(np.sum(y_true == 0))
            roc_auc = (float(np.sum(ranks[y_true == 1])) - positives * (positives + 1) / 2) / (positives * negatives)

            desc = np.argsort(-y_scores, kind="mergesort")
            sorted_desc = y_scores[desc]
            labels_desc = y_true[desc]
            tp_curve = np.cumsum(labels_desc == 1)
            fp_curve = np.cumsum(labels_desc == 0)
            end_indices = np.r_[np.flatnonzero(np.diff(sorted_desc)), len(sorted_desc) - 1]
            precisions = tp_curve[end_indices] / np.maximum(tp_curve[end_indices] + fp_curve[end_indices], 1)
            recalls = tp_curve[end_indices] / positives
            average_precision = float(np.sum(np.diff(np.r_[0.0, recalls]) * precisions))

        return {
            "status": "EVALUATED" if recall is not None else "EVALUATED_SINGLE_CLASS",
            "confusion_matrix": {"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)},
            "accuracy": round((tp + tn) / max(len(y_true), 1), 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4) if recall is not None else None,
            "f1_score": round(f1, 4) if recall is not None else None,
            "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else None,
            "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
            "average_precision": round(average_precision, 4) if average_precision is not None else None,
            "sample_count": int(len(y_true)),
            "positive_count": int(np.sum(y_true == 1))
        }

class DecisionLayerMetrics:
    """Metrics specifically evaluating the Elite Algorithm Decision Intelligence Layer."""

    @staticmethod
    def evaluate_decision_layer(decision_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not decision_records:
            return {"status": "NOT EVALUATED", "reason": "No decision records provided"}

        total_decisions = len(decision_records)
        required = ("ground_truth", "predicted_alert")
        if any(any(key not in row for key in required) for row in decision_records):
            return {"status": "NOT EVALUATED", "reason": "Independent decision labels are required; confidence or gate rates are not false-alert metrics.", "total_decisions_evaluated": total_decisions}
        labels = np.asarray([row["ground_truth"] for row in decision_records], dtype=int)
        preds = np.asarray([row["predicted_alert"] for row in decision_records], dtype=int)
        return {"status": "EVALUATED", "total_decisions_evaluated": total_decisions,
                **ClassificationMetrics.calculate_all(labels, preds)}
