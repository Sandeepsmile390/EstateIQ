"""Statistical metrics utilities for forecasting, anomaly classification, and event detection.

Provides mathematically verified implementations adhering to strict leakage-free
and scientific standards. Handles zero/near-zero edge cases for MAPE and class imbalance.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def calculate_forecasting_metrics(
    y_true: np.ndarray | List[float],
    y_pred: np.ndarray | List[float],
    mape_threshold_kwh: float = 0.5,
) -> Dict[str, Any]:
    """Calculate regression metrics for energy forecasting.

    Args:
        y_true: Ground truth observed energy values (kWh).
        y_pred: Predicted energy values (kWh).
        mape_threshold_kwh: Minimum actual kWh to include in MAPE calculation
            to prevent mathematical distortion from near-zero denominators.

    Returns:
        Dict with mae, rmse, r2, mape, max_error, sample_count, and mape_valid_count.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    if y_t.shape != y_p.shape:
        raise ValueError(f"Shape mismatch: y_true {y_t.shape} vs y_pred {y_p.shape}")

    finite_mask = np.isfinite(y_t) & np.isfinite(y_p)
    y_t = y_t[finite_mask]
    y_p = y_p[finite_mask]

    n = len(y_t)
    if n == 0:
        return {
            "mae": 0.0,
            "rmse": 0.0,
            "r2": 0.0,
            "mape": 0.0,
            "max_error": 0.0,
            "sample_count": 0,
            "mape_valid_count": 0,
        }

    errors = y_t - y_p
    abs_errors = np.abs(errors)
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    ss_tot = float(np.sum((y_t - np.mean(y_t)) ** 2))
    ss_res = float(np.sum(errors ** 2))
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    # Safe MAPE: filter near-zero actual values explicitly
    valid_mape_mask = y_t >= mape_threshold_kwh
    if np.any(valid_mape_mask):
        mape = float(np.mean(abs_errors[valid_mape_mask] / y_t[valid_mape_mask]) * 100.0)
        mape_valid_count = int(np.sum(valid_mape_mask))
    else:
        mape = 0.0
        mape_valid_count = 0

    max_error = float(np.max(abs_errors))

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "mape": round(mape, 2),
        "max_error": round(max_error, 4),
        "sample_count": n,
        "mape_valid_count": mape_valid_count,
    }


def calculate_classification_metrics(
    y_true: np.ndarray | List[int],
    y_pred: np.ndarray | List[int],
    y_scores: Optional[np.ndarray | List[float]] = None,
) -> Dict[str, Any]:
    """Calculate comprehensive classification metrics for anomaly detection.

    Emphasizes precision, recall, F1, and PR-AUC because facility anomaly labels
    are heavily imbalanced.

    Args:
        y_true: Binary ground truth (0 = normal, 1 = anomaly).
        y_pred: Binary predictions (0 = normal, 1 = anomaly).
        y_scores: Optional continuous anomaly scores (e.g. 0-100) for ROC/PR curves.

    Returns:
        Dict with confusion matrix, accuracy, balanced_accuracy, precision, recall,
        specificity, f1_score, false_positive_rate, roc_auc, pr_auc.
    """
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)

    if yt.shape != yp.shape:
        raise ValueError(f"Shape mismatch: y_true {yt.shape} vs y_pred {yp.shape}")

    n = len(yt)
    if n == 0:
        return {
            "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
            "accuracy": 0.0,
            "balanced_accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "specificity": 0.0,
            "f1_score": 0.0,
            "false_positive_rate": 0.0,
            "roc_auc": None,
            "pr_auc": None,
            "sample_count": 0,
            "positive_count": 0,
        }

    tp = int(np.sum((yt == 1) & (yp == 1)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fn = int(np.sum((yt == 1) & (yp == 0)))

    accuracy = (tp + tn) / n if n > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_accuracy = 0.5 * (recall + specificity)
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    roc_auc = None
    pr_auc = None

    if y_scores is not None:
        ys = np.asarray(y_scores, dtype=float)
        finite = np.isfinite(ys)
        yt_sub, ys_sub = yt[finite], ys[finite]

        pos_count = int(np.sum(yt_sub == 1))
        neg_count = int(np.sum(yt_sub == 0))

        if pos_count > 0 and neg_count > 0:
            # Mann-Whitney U for ROC-AUC
            order = np.argsort(ys_sub, kind="mergesort")
            sorted_scores = ys_sub[order]
            ranks = np.empty(len(ys_sub), dtype=float)
            first = 0
            while first < len(order):
                last = first + 1
                while last < len(order) and sorted_scores[last] == sorted_scores[first]:
                    last += 1
                ranks[order[first:last]] = (first + 1 + last) / 2.0
                first = last
            roc_auc = float((np.sum(ranks[yt_sub == 1]) - pos_count * (pos_count + 1) / 2.0) / (pos_count * neg_count))

            # PR-AUC via Average Precision
            desc = np.argsort(-ys_sub, kind="mergesort")
            sorted_desc = ys_sub[desc]
            labels_desc = yt_sub[desc]
            tp_curve = np.cumsum(labels_desc == 1)
            fp_curve = np.cumsum(labels_desc == 0)
            end_indices = np.r_[np.flatnonzero(np.diff(sorted_desc)), len(sorted_desc) - 1]
            precisions = tp_curve[end_indices] / np.maximum(tp_curve[end_indices] + fp_curve[end_indices], 1)
            recalls = tp_curve[end_indices] / pos_count
            pr_auc = float(np.sum(np.diff(np.r_[0.0, recalls]) * precisions))

    return {
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "accuracy": round(accuracy, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc, 4) if pr_auc is not None else None,
        "sample_count": n,
        "positive_count": int(np.sum(yt == 1)),
    }


def calculate_event_level_metrics(
    timestamps: pd.Series | List[Any],
    y_true: np.ndarray | List[int],
    y_pred: np.ndarray | List[int],
    max_gap_minutes: float = 30.0,
) -> Dict[str, Any]:
    """Calculate alert and event-level detection performance across temporal anomaly episodes.

    Groups consecutive positive ground-truth intervals into distinct anomaly events,
    and calculates whether each event was detected and how fast it was caught.

    Args:
        timestamps: Sequence of datetime or ISO strings matching y_true and y_pred.
        y_true: Binary ground truth.
        y_pred: Binary predictions.
        max_gap_minutes: Maximum gap between intervals to consider part of same episode.

    Returns:
        Dict with total_events, detected_events, event_detection_rate,
        mean_detection_delay_minutes, and false_alarm_clusters.
    """
    ts = pd.to_datetime(timestamps, utc=True, errors="coerce")
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)

    if len(ts) != len(yt) or len(yt) != len(yp):
        raise ValueError("Lengths of timestamps, y_true, and y_pred must match")

    df = pd.DataFrame({"timestamp": ts, "truth": yt, "pred": yp}).sort_values("timestamp").reset_index(drop=True)

    # 1. Group true anomaly episodes
    anom_rows = df[df["truth"] == 1].copy()
    if anom_rows.empty:
        return {
            "total_events": 0,
            "detected_events": 0,
            "event_detection_rate": None,
            "mean_detection_delay_minutes": None,
            "false_alarm_clusters": int(np.sum((df["truth"] == 0) & (df["pred"] == 1))),
        }

    anom_rows["gap"] = anom_rows["timestamp"].diff().gt(pd.Timedelta(minutes=max_gap_minutes)).fillna(True)
    anom_rows["episode_id"] = anom_rows["gap"].cumsum()

    total_events = int(anom_rows["episode_id"].nunique())
    detected_events = 0
    delays_min: List[float] = []

    for ep_id, ep_group in anom_rows.groupby("episode_id"):
        start_time = ep_group["timestamp"].min()
        # Find predictions within this episode
        pred_hits = ep_group[ep_group["pred"] == 1]
        if not pred_hits.empty:
            detected_events += 1
            first_alert_time = pred_hits["timestamp"].min()
            delay_minutes = (first_alert_time - start_time).total_seconds() / 60.0
            delays_min.append(max(0.0, delay_minutes))

    event_detection_rate = round(detected_events / total_events, 4) if total_events > 0 else 0.0
    mean_delay = round(float(np.mean(delays_min)), 1) if delays_min else 0.0

    # 2. Count distinct false alarm clusters during normal operation
    norm_preds = df[df["truth"] == 0].copy()
    fa_hits = norm_preds[norm_preds["pred"] == 1].copy()
    if not fa_hits.empty:
        fa_hits["fa_gap"] = fa_hits["timestamp"].diff().gt(pd.Timedelta(minutes=max_gap_minutes)).fillna(True)
        false_alarm_clusters = int(fa_hits["fa_gap"].cumsum().nunique())
    else:
        false_alarm_clusters = 0

    return {
        "total_events": total_events,
        "detected_events": detected_events,
        "event_detection_rate": event_detection_rate,
        "mean_detection_delay_minutes": mean_delay,
        "false_alarm_clusters": false_alarm_clusters,
    }

