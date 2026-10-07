"""
Unified Forecasting Engine & Adapters for Sustainable Facility Intelligence Platform.
Implements problem statement aligned forecasting hierarchy:
Naive Baseline -> Moving Average -> Prophet -> XGBoost -> LightGBM

Provides unified ForecastModel interface, model selection, chronological validation,
and metric tracking (MAE, RMSE, MAPE, R²).
"""

import os
import time
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from abc import ABC, abstractmethod

# Scikit-learn & Gradient Boosting
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# Prophet Forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


class ForecastModel(ABC):
    """Abstract Base Class for unified facility forecasting adapters."""
    
    @abstractmethod
    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "ForecastModel":
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        pass

    def evaluate(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculates standard regression forecasting metrics: MAE, RMSE, MAPE, R2."""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        
        mae = float(np.mean(np.abs(y_true - y_pred)))
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        
        # Avoid division by zero in MAPE
        denom = np.where(np.abs(y_true) < 1e-5, 1e-5, y_true)
        mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)
        
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))
        
        return {
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "MAPE": round(mape, 2),
            "R2": round(r2, 4)
        }


class NaiveForecastAdapter(ForecastModel):
    """Naive baseline forecaster predicting the previous timestamp's value or historical mean."""
    def __init__(self):
        self.last_val = 0.0
        self.mean_val = 0.0

    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "NaiveForecastAdapter":
        y_vals = df[target_col].values
        self.last_val = float(y_vals[-1]) if len(y_vals) > 0 else 0.0
        self.mean_val = float(np.mean(y_vals)) if len(y_vals) > 0 else 0.0
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return np.full(len(df), self.mean_val)


class MovingAverageForecastAdapter(ForecastModel):
    """Moving Average forecaster using rolling window average."""
    def __init__(self, window: int = 24):
        self.window = window
        self.avg_val = 0.0

    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "MovingAverageForecastAdapter":
        y_vals = df[target_col].values
        if len(y_vals) >= self.window:
            self.avg_val = float(np.mean(y_vals[-self.window:]))
        else:
            self.avg_val = float(np.mean(y_vals)) if len(y_vals) > 0 else 0.0
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return np.full(len(df), self.avg_val)


class ProphetForecastAdapter(ForecastModel):
    """Prophet time-series forecasting model adapter."""
    def __init__(self, yearly_seasonality: bool = False, weekly_seasonality: bool = True, daily_seasonality: bool = True):
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.model = None

    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "ProphetForecastAdapter":
        if not PROPHET_AVAILABLE:
            raise RuntimeError("Prophet library is not installed.")
        
        pdf = pd.DataFrame({
            "ds": pd.to_datetime(df[timestamp_col]),
            "y": df[target_col].values
        })
        
        self.model = Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality
        )
        self.model.fit(pdf)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Prophet model is not fitted yet.")
        pdf = pd.DataFrame({"ds": pd.to_datetime(df["ds"])})
        forecast = self.model.predict(pdf)
        return forecast["yhat"].values


class XGBoostForecastAdapter(ForecastModel):
    """XGBoost Regressor forecast adapter for structured tabular feature matrices."""
    def __init__(self, n_estimators: int = 100, max_depth: int = 6, learning_rate: float = 0.05):
        self.model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            verbosity=0
        )
        self.feature_cols = []

    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "XGBoostForecastAdapter":
        if feature_cols is None:
            self.feature_cols = [c for c in df.columns if c not in [timestamp_col, target_col]]
        else:
            self.feature_cols = feature_cols
            
        X = df[self.feature_cols]
        y = df[target_col]
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_cols]
        return self.model.predict(X)


class LightGBMForecastAdapter(ForecastModel):
    """LightGBM Regressor forecast adapter."""
    def __init__(self, n_estimators: int = 100, max_depth: int = 6, learning_rate: float = 0.05):
        self.model = LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42,
            verbose=-1
        )
        self.feature_cols = []

    def fit(self, df: pd.DataFrame, timestamp_col: str = "ds", target_col: str = "y", feature_cols: Optional[List[str]] = None) -> "LightGBMForecastAdapter":
        if feature_cols is None:
            self.feature_cols = [c for c in df.columns if c not in [timestamp_col, target_col]]
        else:
            self.feature_cols = feature_cols
            
        X = df[self.feature_cols]
        y = df[target_col]
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_cols]
        return self.model.predict(X)


class UnifiedForecastingEngine:
    """
    Unified Forecasting Model Selector executing model comparison:
    Naive Baseline -> Moving Average -> Prophet -> XGBoost -> LightGBM
    """
    def __init__(self, output_dir: str = "models"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def evaluate_all(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        timestamp_col: str = "ds",
        target_col: str = "y",
        feature_cols: Optional[List[str]] = None
    ) -> Tuple[ForecastModel, pd.DataFrame, Dict[str, Any]]:
        """Evaluates all candidate forecast adapters using chronological validation."""
        
        candidates = {
            "Naive Baseline": NaiveForecastAdapter(),
            "Moving Average (24h)": MovingAverageForecastAdapter(window=24),
            "XGBoost Forecast": XGBoostForecastAdapter(n_estimators=60),
            "LightGBM Forecast": LightGBMForecastAdapter(n_estimators=60)
        }
        
        if PROPHET_AVAILABLE:
            candidates["Prophet Forecast"] = ProphetForecastAdapter()

        results = []
        fitted_models = {}

        for name, model in candidates.items():
            t0 = time.time()
            try:
                model.fit(train_df, timestamp_col=timestamp_col, target_col=target_col, feature_cols=feature_cols)
                train_time = round(time.time() - t0, 4)

                t1 = time.time()
                preds = model.predict(val_df)
                inf_time = round(time.time() - t1, 4)

                metrics = model.evaluate(val_df[target_col].values, preds)
                row = {
                    "Model": name,
                    "MAE": metrics["MAE"],
                    "RMSE": metrics["RMSE"],
                    "MAPE": metrics["MAPE"],
                    "R2": metrics["R2"],
                    "Training_Time_s": train_time,
                    "Inference_Time_s": inf_time,
                    "Status": "SUCCESS"
                }
                fitted_models[name] = model
            except Exception as e:
                row = {
                    "Model": name,
                    "MAE": 99999.0,
                    "RMSE": 99999.0,
                    "MAPE": 100.0,
                    "R2": -1.0,
                    "Training_Time_s": 0.0,
                    "Inference_Time_s": 0.0,
                    "Status": f"FAILED: {str(e)}"
                }
            results.append(row)

        df_comp = pd.DataFrame(results)
        
        # Select model minimizing RMSE among successful candidates
        valid_comp = df_comp[df_comp["Status"] == "SUCCESS"]
        best_row = valid_comp.sort_values(by="RMSE").iloc[0]
        best_name = best_row["Model"]
        best_model = fitted_models[best_name]

        metadata = {
            "model_name": best_name,
            "model_version": "2.0.0",
            "training_period": f"{train_df[timestamp_col].min()} to {train_df[timestamp_col].max()}",
            "validation_metrics": {
                "MAE": float(best_row["MAE"]),
                "RMSE": float(best_row["RMSE"]),
                "MAPE": float(best_row["MAPE"]),
                "R2": float(best_row["R2"])
            },
            "features": feature_cols if feature_cols else [c for c in train_df.columns if c not in [timestamp_col, target_col]],
            "model_hierarchy": ["Naive Baseline", "Moving Average", "Prophet", "XGBoost", "LightGBM"]
        }

        # Save model and metadata
        joblib.dump(best_model, os.path.join(self.output_dir, "forecast_best_model.joblib"))
        joblib.dump(metadata, os.path.join(self.output_dir, "forecast_metadata.joblib"))

        return best_model, df_comp, metadata
