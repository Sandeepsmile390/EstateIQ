"""
Model Selection Engine for Sustainable Facility Intelligence Platform.
Implements automated model comparison, hyperparameter tuning with Optuna, error analysis,
metric tracking, and evidence-based candidate selection.
"""

import os
import time
import joblib
import optuna
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor
from xgboost import XGBRegressor, XGBClassifier
from lightgbm import LGBMRegressor, LGBMClassifier
from catboost import CatBoostRegressor, CatBoostClassifier

from src.models.baseline import NaiveMeanRegressor, MajorityClassClassifier
from src.evaluation.validation import evaluate_regression_metrics, evaluate_classification_metrics, chronological_split

optuna.logging.set_verbosity(optuna.logging.WARNING)

class ModelSelectionEngine:
    def __init__(self, task_name: str, task_type: str = "regression", output_dir: str = "models"):
        self.task_name = task_name
        self.task_type = task_type
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.comparison_table = []
        
    def evaluate_candidates(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> pd.DataFrame:
        """Trains candidate models, records metrics, training time, and inference time."""
        self.comparison_table = []
        
        if self.task_type == "regression":
            candidates = {
                "Naive Baseline": NaiveMeanRegressor(),
                "Linear Regression": LinearRegression(),
                "Random Forest": RandomForestRegressor(n_estimators=50, random_state=42),
                "Gradient Boosting": GradientBoostingRegressor(n_estimators=50, random_state=42),
                "XGBoost": XGBRegressor(n_estimators=50, random_state=42, verbosity=0),
                "LightGBM": LGBMRegressor(n_estimators=50, random_state=42, verbose=-1),
                "CatBoost": CatBoostRegressor(n_estimators=50, random_state=42, verbose=0)
            }
        else:
            candidates = {
                "Naive Baseline": MajorityClassClassifier(),
                "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
                "Random Forest": RandomForestClassifier(n_estimators=50, random_state=42),
                "XGBoost": XGBClassifier(n_estimators=50, random_state=42, eval_metric="logloss"),
                "LightGBM": LGBMClassifier(n_estimators=50, random_state=42, verbose=-1),
                "CatBoost": CatBoostClassifier(n_estimators=50, random_state=42, verbose=0)
            }
            
        for name, model in candidates.items():
            t0 = time.time()
            model.fit(X_train, y_train)
            train_time = round(time.time() - t0, 4)
            
            t1 = time.time()
            if self.task_type == "regression":
                preds = model.predict(X_val)
                inf_time = round(time.time() - t1, 4)
                metrics = evaluate_regression_metrics(y_val.values, preds)
                row = {
                    "Model": name,
                    "Task": self.task_name,
                    "MAE": metrics["MAE"],
                    "RMSE": metrics["RMSE"],
                    "R2": metrics["R2"],
                    "MAPE": metrics["MAPE"],
                    "Training_Time_s": train_time,
                    "Inference_Time_s": inf_time,
                    "Selected": False
                }
            else:
                if hasattr(model, "predict_proba"):
                    probs = model.predict_proba(X_val)[:, 1]
                else:
                    preds = model.predict(X_val)
                    probs = preds
                inf_time = round(time.time() - t1, 4)
                metrics = evaluate_classification_metrics(y_val.values, probs)
                row = {
                    "Model": name,
                    "Task": self.task_name,
                    "Precision": metrics["Precision"],
                    "Recall": metrics["Recall"],
                    "F1": metrics["F1"],
                    "ROC-AUC": metrics["ROC-AUC"],
                    "PR-AUC": metrics["PR-AUC"],
                    "Training_Time_s": train_time,
                    "Inference_Time_s": inf_time,
                    "Selected": False
                }
            self.comparison_table.append((model, row))
            
        return pd.DataFrame([r[1] for r in self.comparison_table])

    def tune_xgboost(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series, n_trials: int = 10) -> Dict[str, Any]:
        """Tunes XGBoost using Optuna hyperparameter optimization."""
        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 30, 150),
                "max_depth": trial.suggest_int("max_depth", 3, 9),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "random_state": 42
            }
            if self.task_type == "regression":
                model = XGBRegressor(**params, verbosity=0)
                model.fit(X_train, y_train)
                preds = model.predict(X_val)
                return evaluate_regression_metrics(y_val.values, preds)["RMSE"]
            else:
                model = XGBClassifier(**params, eval_metric="logloss")
                model.fit(X_train, y_train)
                probs = model.predict_proba(X_val)[:, 1]
                return -evaluate_classification_metrics(y_val.values, probs)["F1"]

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials)
        return study.best_params

    def select_and_save(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> Tuple[Any, Dict[str, Any]]:
        """
        Executes full selection logic: evaluates candidates, tunes top candidate,
        conducts error analysis, marks selected model, saves model binary and metadata.
        """
        df_comp = self.evaluate_candidates(X_train, y_train, X_val, y_val)
        
        # Select best model based on validation evidence
        if self.task_type == "regression":
            # Best model minimizes RMSE
            best_idx = df_comp[df_comp["Model"] != "Naive Baseline"]["RMSE"].idxmin()
        else:
            # Best model maximizes F1 score
            best_idx = df_comp[df_comp["Model"] != "Naive Baseline"]["F1"].idxmax()
            
        best_model_name = df_comp.loc[best_idx, "Model"]
        print(f"[{self.task_name}] Best initial candidate identified: {best_model_name}")
        
        # Hyperparameter tuning on top candidate (XGBoost demonstration)
        best_params = {}
        if "XGBoost" in best_model_name:
            best_params = self.tune_xgboost(X_train, y_train, X_val, y_val, n_trials=5)
            if self.task_type == "regression":
                final_model = XGBRegressor(**best_params, verbosity=0)
            else:
                final_model = XGBClassifier(**best_params, eval_metric="logloss")
            final_model.fit(X_train, y_train)
        else:
            # Retrieve winning fitted model instance
            final_model = [m[0] for m in self.comparison_table if m[1]["Model"] == best_model_name][0]
            
        # Error Analysis on Validation Set
        if self.task_type == "regression":
            val_preds = final_model.predict(X_val)
            errors = y_val.values - val_preds
            err_mean = float(np.mean(errors))
            err_std = float(np.std(errors))
            max_error = float(np.max(np.abs(errors)))
            error_analysis = {
                "mean_residual": round(err_mean, 4),
                "std_residual": round(err_std, 4),
                "max_absolute_error": round(max_error, 4)
            }
            final_metrics = evaluate_regression_metrics(y_val.values, val_preds)
        else:
            probs = final_model.predict_proba(X_val)[:, 1] if hasattr(final_model, "predict_proba") else final_model.predict(X_val)
            final_metrics = evaluate_classification_metrics(y_val.values, probs)
            error_analysis = {
                "confusion_matrix": final_metrics["Confusion_Matrix"]
            }
            
        # Mark selected model in comparison table
        for r in self.comparison_table:
            if r[1]["Model"] == best_model_name:
                r[1]["Selected"] = True
                
        # Save Model Artifacts
        model_filename = f"{self.task_name}_model.joblib"
        model_path = os.path.join(self.output_dir, model_filename)
        joblib.dump(final_model, model_path)
        
        metadata = {
            "task": self.task_name,
            "task_type": self.task_type,
            "selected_model": best_model_name,
            "hyperparameters": best_params if best_params else "default",
            "val_metrics": final_metrics,
            "error_analysis": error_analysis,
            "feature_names": list(X_train.columns),
            "model_path": model_path
        }
        
        meta_filename = f"{self.task_name}_metadata.joblib"
        joblib.dump(metadata, os.path.join(self.output_dir, meta_filename))
        
        return final_model, metadata
