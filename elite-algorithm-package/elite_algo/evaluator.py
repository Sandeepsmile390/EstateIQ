"""Reproducible evaluation of Elite-DIF and honest reference baselines.

All bundled facility readings are generated/simulated. Results from this module
are therefore internal synthetic-data evidence, not production generalization.
The anomaly experiment selects known injected episodes for evaluation, but the
baseline model itself never consumes anomaly labels.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elite_algo.metrics import ClassificationMetrics, ForecastingMetrics
from src.intelligence.config import DIFConfig
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.types import EventData


RAW_DATA = PROJECT_ROOT / "facility_dataset" / "data" / "raw"


class PackageEvaluator:
    """Evaluate with chronological baselines and injected anomaly labels."""

    def __init__(self, data_dir: Path = RAW_DATA):
        self.data_dir = Path(data_dir)

    def evaluate_all(self) -> Dict[str, Any]:
        energy = self.evaluate_energy_forecasting()
        water = self.evaluate_water_forecasting()
        waste = self.evaluate_waste_prediction()
        anomaly = self.evaluate_anomaly_detection()
        decision = self.evaluate_decision_layer()
        rows = []
        for name, result in (("15-minute persistence", energy["naive_metrics"]),
                             ("7-day seasonal naive", energy["specialist_metrics"])):
            for metric in ("mae", "rmse", "r2"):
                val = result.get(metric)
                rows.append({"Metric": metric.upper(), "Metric Name": metric.upper(),
                             "Component": name, "Value": val, "Measured Value": val,
                             "Unit": "kWh per 15-minute interval",
                             "Samples": energy["sample_count"],
                             "Evaluation": energy["evaluation_protocol"],
                             "Provenance": energy["provenance"]})
        for metric in ("precision", "recall", "f1_score", "false_positive_rate", "roc_auc", "average_precision"):
            val = anomaly.get(metric)
            rows.append({"Metric": metric, "Metric Name": metric,
                         "Component": "EstateIQ-DIF anomaly score",
                         "Value": val, "Measured Value": val,
                         "Unit": "dimensionless",
                         "Samples": anomaly.get("sample_count", 0),
                         "Evaluation": anomaly.get("evaluation_protocol", "NOT EVALUATED"),
                         "Provenance": anomaly.get("provenance", "NOT EVALUATED")})
        return {
            "energy_results": energy,
            "water_results": water,
            "waste_results": waste,
            "anomaly_results": anomaly,
            "decision_results": decision,
            "summary_df": pd.DataFrame(rows),
        }

    def _read(self, file_name: str, columns: Iterable[str]) -> pd.DataFrame:
        path = self.data_dir / file_name
        if not path.exists():
            return pd.DataFrame()
        frame = pd.read_csv(path, usecols=lambda col: col in set(columns),
                            parse_dates=["timestamp"] if "timestamp" in columns else None)
        return frame

    def evaluate_energy_forecasting(self) -> Dict[str, Any]:
        df = self._read("energy_readings.csv", ["timestamp", "building_id", "electricity_kwh"])
        if df.empty or "electricity_kwh" not in df:
            return {"status": "NOT EVALUATED", "reason": "Raw energy readings unavailable"}
        df = df.sort_values(["building_id", "timestamp"]).reset_index(drop=True)
        y_true, weekly, persistence, mean_preds = [], [], [], []
        test_times = []
        lag = 7 * 24 * 4
        for _, group in df.groupby("building_id", sort=False):
            vals = pd.to_numeric(group["electricity_kwh"], errors="coerce").to_numpy(dtype=float)
            start = int(len(vals) * 0.85)
            train = vals[:int(len(vals) * 0.70)]
            begin = max(start, lag)
            target = vals[begin:]
            seasonal = vals[begin - lag:len(vals) - lag]
            previous = vals[begin - 1:-1]
            finite = np.isfinite(target) & np.isfinite(seasonal) & np.isfinite(previous)
            target, seasonal, previous = target[finite], seasonal[finite], previous[finite]
            y_true.extend(target.tolist()); weekly.extend(seasonal.tolist())
            persistence.extend(previous.tolist())
            mean_preds.extend(np.full(len(target), np.nanmean(train)).tolist())
            test_times.extend(group["timestamp"].iloc[begin:].tolist())
        y = np.asarray(y_true, dtype=float)
        return {
            "status": "EVALUATED",
            "model_name": "7-day seasonal naive reference (not a trained Elite model)",
            "sample_count": int(len(y)),
            "test_start": min(test_times).isoformat() if test_times else None,
            "test_end": max(test_times).isoformat() if test_times else None,
            "evaluation_protocol": "Per-building chronological 70/15/15; final 15% one-step rolling-origin; weekly lag 672",
            "provenance": "SIMULATED_IOT_GENERATED_DATASET",
            "y_true": y,
            "y_pred_specialist": np.asarray(weekly),
            "y_pred_naive": np.asarray(persistence),
            "y_pred_mean": np.asarray(mean_preds),
            "specialist_metrics": ForecastingMetrics.calculate_all(y, weekly),
            "naive_metrics": ForecastingMetrics.calculate_all(y, persistence),
            "mean_metrics": ForecastingMetrics.calculate_all(y, mean_preds),
        }

    def evaluate_water_forecasting(self) -> Dict[str, Any]:
        # Water models are outside the Elite-DIF execution path. Do not synthesize
        # predictions or relabel generated values as specialist-model accuracy.
        return {"status": "NOT EVALUATED", "reason": "No independent, held-out water model predictions are wired to Elite-DIF."}

    def evaluate_waste_prediction(self) -> Dict[str, Any]:
        # Overflow risk and generated overflow labels are part of a separate
        # synthetic domain module and do not measure the Elite energy decision path.
        return {"status": "NOT EVALUATED", "reason": "Waste overflow is outside Elite-DIF and has no independent evaluation protocol here."}

    def evaluate_anomaly_detection(self) -> Dict[str, Any]:
        df = self._read("energy_readings.csv", ["timestamp", "building_id", "electricity_kwh", "anomaly_flag"])
        required = {"timestamp", "building_id", "electricity_kwh", "anomaly_flag"}
        if df.empty or not required.issubset(df.columns):
            return {"status": "NOT EVALUATED", "reason": "Labeled energy readings unavailable"}
        df = df.sort_values(["building_id", "timestamp"]).reset_index(drop=True)
        labeled = df[pd.to_numeric(df["anomaly_flag"], errors="coerce").fillna(0).astype(int) == 1]
        episodes = []
        for building, group in labeled.groupby("building_id", sort=False):
            group = group.sort_values("timestamp")
            # Label continuity is used only to delimit the evaluation windows.
            cut = group["timestamp"].diff().gt(pd.Timedelta(minutes=15)).fillna(True)
            for _, episode in group.groupby(cut.cumsum()):
                episodes.append((building, episode["timestamp"].min(), episode["timestamp"].max()))
        if not episodes:
            return {"status": "NOT EVALUATED", "reason": "No labeled anomaly episodes found"}

        truths, scores, preds, y, yhat, global_yhat = [], [], [], [], [], []
        for building, start, end in episodes:
            history = df[(df["building_id"] == building) & (df["timestamp"] < start)]
            try:
                profile = SeasonalBaselineModel(min_observations=4).fit(history)
            except ValueError:
                continue
            window = df[(df["building_id"] == building)
                        & (df["timestamp"] >= start - pd.Timedelta(hours=24))
                        & (df["timestamp"] <= end + pd.Timedelta(hours=24))]
            engine = EstateIQDIF(config=DIFConfig(), baseline_model=profile)
            train_median = float(pd.to_numeric(history["electricity_kwh"], errors="coerce").median())
            for idx, row in enumerate(window.itertuples(index=False)):
                stamp = pd.Timestamp(row.timestamp)
                event = EventData(
                    event_id=f"RESEARCH-{building}-{idx}", facility_id="SYNTHETIC-CAMPUS",
                    building_id=str(building), timestamp=stamp.isoformat(),
                    actual_kwh=float(row.electricity_kwh), hour=int(stamp.hour),
                    day_of_week=int(stamp.dayofweek), occupancy=0, temperature=25.0,
                    hvac_load=0.0, extra_features={}, interval_hours=0.25,
                )
                result = engine.analyze(event)
                truth = int(row.anomaly_flag)
                score = float(result.anomaly.anomaly_score)
                truths.append(truth); scores.append(score)
                preds.append(int(score >= engine.config.anomaly_score_threshold))
                y.append(float(row.electricity_kwh)); yhat.append(result.contextual.expected_kwh)
                global_yhat.append(train_median)

        if not truths:
            return {"status": "NOT EVALUATED", "reason": "No anomaly window had sufficient past seasonal training data"}
        result = ClassificationMetrics.calculate_all(np.asarray(truths), np.asarray(preds), np.asarray(scores))
        return {
            **result,
            "status": result["status"],
            "evaluation_protocol": "Two generated, labeled energy-injection episodes; training history strictly precedes each episode; ±24-hour windows; score threshold fixed at 55/100",
            "provenance": "SYNTHETIC_INJECTED_ANOMALIES_NOT_REAL_FACILITY_VALIDATION",
            "baseline_metrics": ForecastingMetrics.calculate_all(y, yhat),
            "building_median_reference_metrics": ForecastingMetrics.calculate_all(y, global_yhat),
            "episode_count": len(episodes),
            "sample_count": len(truths),
            "threshold": 55.0,
            "threshold_selection": "Pre-specified configuration default; not tuned on these test labels",
            "y_true": truths,
            "y_score": scores,
            "y_pred": preds,
        }

    def evaluate_decision_layer(self) -> Dict[str, Any]:
        return {"status": "NOT EVALUATED", "reason": "No independent operator decision labels; confidence and priority are not accuracy measures."}
