"""
Feature Engineering Module for Sustainable Facility System.
Transforms raw sensor datasets into ML-ready features safely without lookahead bias or future data leakage.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple

def extract_time_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Extracts temporal features from timestamp."""
    df_feat = df.copy()
    if timestamp_col in df_feat.columns:
        df_feat[timestamp_col] = pd.to_datetime(df_feat[timestamp_col])
        df_feat["hour"] = df_feat[timestamp_col].dt.hour
        df_feat["day_of_week"] = df_feat[timestamp_col].dt.dayofweek
        df_feat["month"] = df_feat[timestamp_col].dt.month
        df_feat["is_weekend"] = (df_feat["day_of_week"] >= 5).astype(int)
        df_feat["is_peak_hour"] = df_feat["hour"].apply(lambda h: 1 if 8 <= h <= 18 else 0)
        # Cyclical encoding for hour
        df_feat["hour_sin"] = np.sin(2 * np.pi * df_feat["hour"] / 24.0)
        df_feat["hour_cos"] = np.cos(2 * np.pi * df_feat["hour"] / 24.0)
    return df_feat

def add_lag_and_rolling_features(df: pd.DataFrame, group_col: str, target_col: str, lags: List[int] = [1, 2, 24], windows: List[int] = [3, 6, 24]) -> pd.DataFrame:
    """
    Computes lag and rolling window statistics strictly historical-only to prevent lookahead leakage.
    """
    df_feat = df.sort_values(by=["timestamp"]).copy()
    
    if group_col in df_feat.columns:
        grouped = df_feat.groupby(group_col)
        for lag in lags:
            df_feat[f"{target_col}_lag_{lag}"] = grouped[target_col].shift(lag)
        for w in windows:
            df_feat[f"{target_col}_rolling_mean_{w}"] = grouped[target_col].shift(1).rolling(w).mean()
            df_feat[f"{target_col}_rolling_std_{w}"] = grouped[target_col].shift(1).rolling(w).std()
    else:
        for lag in lags:
            df_feat[f"{target_col}_lag_{lag}"] = df_feat[target_col].shift(lag)
        for w in windows:
            df_feat[f"{target_col}_rolling_mean_{w}"] = df_feat[target_col].shift(1).rolling(w).mean()
            df_feat[f"{target_col}_rolling_std_{w}"] = df_feat[target_col].shift(1).rolling(w).std()
            
    return df_feat.bfill().fillna(0)

def prepare_feature_matrix(df: pd.DataFrame, target_col: str, drop_cols: List[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepares feature matrix X and target vector y with standard one-hot encoding for categorical variables."""
    if drop_cols is None:
        drop_cols = ["timestamp", "facility_id", "is_synthetic"]
        
    df_clean = df.copy()
    cols_to_drop = [c for c in drop_cols if c in df_clean.columns]
    if target_col in df_clean.columns:
        y = df_clean[target_col]
        cols_to_drop.append(target_col)
    else:
        y = None
        
    X = df_clean.drop(columns=cols_to_drop)
    # Convert categorical strings to dummy indicators
    X = pd.get_dummies(X, drop_first=True)
    return X, y
