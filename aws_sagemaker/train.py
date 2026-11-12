"""SageMaker script-mode trainer for the EstateIQ learned anomaly evidence model.

Trains the existing, benchmarked Random Forest candidate on building-fault labels.
This is a learned component for future DIF integration, not a claim that all DIF
logic is learned. The sensor-quality engine remains a separate detector.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

FEATURE_NAMES = [
    "electricity_kwh", "hvac_kwh", "lighting_kwh", "equipment_kwh", "other_kwh",
    "power_factor", "temperature_c", "occupancy_count", "hvac_ratio", "lighting_ratio",
    "equipment_ratio", "sin_hour", "cos_hour", "sin_dow", "cos_dow", "is_weekend",
]
RAW_FEATURES = ["electricity_kwh", "hvac_kwh", "lighting_kwh", "equipment_kwh",
                "other_kwh", "power_factor", "temperature_c", "occupancy_count"]


def load_channel(path: Path) -> pd.DataFrame:
    files = sorted(path.glob("*.csv")) if path.exists() else []
    if not files:
        raise FileNotFoundError(f"No CSV found in SageMaker input channel {path}")
    return pd.concat([pd.read_csv(item) for item in files], ignore_index=True)


def features(frame: pd.DataFrame) -> np.ndarray:
    # Keep this calculation aligned with src.benchmarks.model_training_bench.
    ts = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    hour = ts.dt.hour.to_numpy(dtype=float) + ts.dt.minute.to_numpy(dtype=float) / 60.0
    dow = ts.dt.dayofweek.to_numpy(dtype=float)
    values: dict[str, np.ndarray] = {}
    defaults = {"electricity_kwh": 0.0, "hvac_kwh": 0.0, "lighting_kwh": 0.0,
                "equipment_kwh": 0.0, "other_kwh": 0.0, "power_factor": 0.95,
                "temperature_c": 25.0, "occupancy_count": 0.0}
    for name in RAW_FEATURES:
        values[name] = pd.to_numeric(frame[name], errors="coerce").fillna(defaults[name]).to_numpy(dtype=float) if name in frame else np.full(len(frame), defaults[name], dtype=float)
    denominator = np.maximum(values["electricity_kwh"], 1e-3)
    matrix = np.column_stack([
        values["electricity_kwh"], values["hvac_kwh"], values["lighting_kwh"],
        values["equipment_kwh"], values["other_kwh"], values["power_factor"],
        values["temperature_c"], values["occupancy_count"],
        values["hvac_kwh"] / denominator, values["lighting_kwh"] / denominator,
        values["equipment_kwh"] / denominator,
        np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
        np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7), (dow >= 5).astype(float),
    ])
    return np.nan_to_num(matrix, nan=0.0, posinf=1e4, neginf=-1e4)


def labels(frame: pd.DataFrame) -> np.ndarray:
    if "target_anomaly" not in frame:
        raise ValueError("Input channel must contain target_anomaly from prepare_data.py")
    return pd.to_numeric(frame["target_anomaly"], errors="raise").to_numpy(dtype=int)


def choose_threshold(y_true: np.ndarray, scores: np.ndarray, exposure_building_days: float,
                     false_alert_budget: float) -> dict[str, Any]:
    candidates = np.unique(np.r_[0.0, scores, 1.000001])
    best: tuple[float, float, int, float] | None = None
    feasible_count = 0
    for threshold in candidates:
        pred = (scores >= threshold).astype(int)
        fp = int(np.sum((y_true == 0) & (pred == 1)))
        fp_per_day = fp / max(exposure_building_days, 1e-9)
        if fp_per_day > false_alert_budget:
            continue
        feasible_count += 1
        f1 = float(f1_score(y_true, pred, zero_division=0))
        precision = float(precision_score(y_true, pred, zero_division=0))
        candidate = (f1, precision, -fp, float(threshold))
        if best is None or candidate > best:
            best = candidate
    if best is None:
        # Fail closed if validation cannot meet the stated alert budget.
        return {"threshold": 1.000001, "validation_budget_met": False, "feasible_thresholds": 0}
    return {"threshold": best[3], "validation_budget_met": True, "feasible_thresholds": feasible_count}


def evaluate(name: str, frame: pd.DataFrame, y_true: np.ndarray, scores: np.ndarray,
             threshold: float) -> dict[str, Any]:
    predicted = (scores >= threshold).astype(int)
    tn, fp, fn, tp = (int(x) for x in confusion_matrix(y_true, predicted, labels=[0, 1]).ravel())
    exposure_days = len(frame) / 96.0  # 15-minute data: 96 readings per building-day.
    result: dict[str, Any] = {
        "split": name, "rows": int(len(frame)), "positives": int(y_true.sum()),
        "threshold": float(threshold), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": float(precision_score(y_true, predicted, zero_division=0)),
        "recall": float(recall_score(y_true, predicted, zero_division=0)),
        "f1": float(f1_score(y_true, predicted, zero_division=0)),
        "false_alerts_per_building_day": float(fp / max(exposure_days, 1e-9)),
        "average_precision": float(average_precision_score(y_true, scores)) if y_true.sum() else None,
        "roc_auc": float(roc_auc_score(y_true, scores)) if np.unique(y_true).size == 2 else None,
    }
    if "event_id" in frame:
        actual = frame.loc[y_true == 1, "event_id"].dropna().astype(str)
        event_ids = sorted(set(value for value in actual if value and value.lower() != "nan"))
        captured = 0
        for event_id in event_ids:
            rows = frame["event_id"].astype(str).to_numpy() == event_id
            captured += int(bool(np.any(predicted[rows] == 1)))
        result["actual_events"] = len(event_ids)
        result["captured_events"] = captured
        result["event_capture_rate"] = captured / len(event_ids) if event_ids else None
    if "building_id" in frame:
        result["per_building_false_alerts"] = {
            str(building): int(np.sum((frame["building_id"].astype(str).to_numpy() == str(building)) & (y_true == 0) & (predicted == 1)))
            for building in sorted(frame["building_id"].astype(str).unique())
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--min-samples-leaf", type=int, default=2)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--false-alert-budget", type=float, default=1.0)
    args, _ = parser.parse_known_args()

    input_root = Path(os.getenv("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    train_df = load_channel(input_root)
    validation_df = load_channel(Path(os.getenv("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation")))
    test_df = load_channel(Path(os.getenv("SM_CHANNEL_TEST", "/opt/ml/input/data/test")))
    holdout_df = load_channel(Path(os.getenv("SM_CHANNEL_BUILDING_HOLDOUT", "/opt/ml/input/data/building_holdout")))

    y_train = labels(train_df)
    if np.unique(y_train).size != 2:
        raise ValueError("Training data must contain both nominal and building-fault examples")
    model = Pipeline([
        ("scale", StandardScaler()),
        ("classifier", RandomForestClassifier(
            n_estimators=args.n_estimators, max_depth=args.max_depth,
            min_samples_leaf=args.min_samples_leaf, class_weight="balanced",
            random_state=args.random_seed, n_jobs=1,
        )),
    ])
    model.fit(features(train_df), y_train)

    y_validation = labels(validation_df)
    validation_scores = model.predict_proba(features(validation_df))[:, 1]
    calibration = choose_threshold(y_validation, validation_scores,
                                   len(validation_df) / 96.0, args.false_alert_budget)
    threshold = float(calibration["threshold"])

    reports = {
        "validation": evaluate("validation", validation_df, y_validation, validation_scores, threshold),
        "test": evaluate("test", test_df, labels(test_df), model.predict_proba(features(test_df))[:, 1], threshold),
        "building_holdout": evaluate("building_holdout", holdout_df, labels(holdout_df), model.predict_proba(features(holdout_df))[:, 1], threshold),
    }
    metadata = {
        "model_name": "EstateIQ-Learned-Anomaly-Evidence-v1",
        "model_type": "RandomForestClassifier with StandardScaler",
        "target": "synthetic building_fault vs nominal; sensor faults excluded",
        "feature_names": FEATURE_NAMES,
        "threshold": threshold,
        "threshold_calibrated_on": "validation only",
        "false_alert_budget_per_building_day": args.false_alert_budget,
        "validation_budget_met": calibration["validation_budget_met"],
        "training_rows": int(len(train_df)),
        "training_positive_rows": int(y_train.sum()),
        "training_buildings": sorted(train_df["building_id"].astype(str).unique().tolist()),
        "test_protocol": "future period on training buildings and a separate fully unseen building",
        "metrics": reports,
        "limitations": [
            "trained only on the supplied synthetic dataset; real-sensor performance is unverified",
            "this is a learned evidence component, not the complete EstateIQ-DIF pipeline",
            "model probabilities are ranking scores and are not claimed to be calibrated probabilities",
        ],
    }

    model_dir = Path(os.getenv("SM_MODEL_DIR", "/opt/ml/model"))
    output_dir = Path(os.getenv("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data"))
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "metadata": metadata}, model_dir / "estateiq_anomaly_model.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    print("ESTATEIQ_TRAINING_METRICS=" + json.dumps(metadata, allow_nan=False))


if __name__ == "__main__":
    main()
