"""
Time-Series Aware Validation & Evaluation Engine.
Enforces chronological train/val/test splits, walk-forward validation,
data leakage checks, and standardized metric calculations for regression and classification.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, auc, confusion_matrix
)

def evaluate_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculates standardized regression metrics: MAE, RMSE, R2, MAPE, sMAPE."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    
    # Avoid zero division in MAPE
    epsilon = 1e-8
    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + epsilon))) * 100.0)
    smape = float(np.mean(2.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + epsilon)) * 100.0)
    
    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
        "MAPE": round(mape, 2),
        "sMAPE": round(smape, 2)
    }

def evaluate_classification_metrics(y_true: np.ndarray, y_pred_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """Calculates standardized classification metrics: Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix."""
    y_true = np.array(y_true, dtype=int)
    y_pred_prob = np.array(y_pred_prob, dtype=float)
    y_pred_binary = (y_pred_prob >= threshold).astype(int)
    
    prec = float(precision_score(y_true, y_pred_binary, zero_division=0))
    rec = float(recall_score(y_true, y_pred_binary, zero_division=0))
    f1 = float(f1_score(y_true, y_pred_binary, zero_division=0))
    
    try:
        roc_auc = float(roc_auc_score(y_true, y_pred_prob))
    except Exception:
        roc_auc = 0.5
        
    p, r, _ = precision_recall_curve(y_true, y_pred_prob)
    pr_auc = float(auc(r, p))
    cm = confusion_matrix(y_true, y_pred_binary).tolist()
    
    return {
        "Precision": round(prec, 4),
        "Recall": round(rec, 4),
        "F1": round(f1, 4),
        "ROC-AUC": round(roc_auc, 4),
        "PR-AUC": round(pr_auc, 4),
        "Confusion_Matrix": cm
    }

def chronological_split(df: pd.DataFrame, time_col: str = "timestamp", train_ratio: float = 0.7, val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Performs chronological Train / Validation / Test split.
    CRITICAL: Never randomly shuffle time-series data to avoid target leakage & lookahead bias!
    """
    df_sorted = df.sort_values(by=time_col).reset_index(drop=True)
    n = len(df_sorted)
    
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()
    
    return train_df, val_df, test_df

def detect_target_leakage(features_df: pd.DataFrame, target: pd.Series, threshold: float = 0.98) -> List[str]:
    """Detects potential target leakage by checking for suspiciously high correlation with target."""
    suspicious_features = []
    for col in features_df.select_dtypes(include=[np.number]).columns:
        corr = features_df[col].corr(target)
        if abs(corr) >= threshold:
            suspicious_features.append(col)
    return suspicious_features
