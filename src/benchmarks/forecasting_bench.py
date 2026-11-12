"""Energy forecasting benchmark engine.

Evaluates candidate and baseline energy forecasting methods strictly on chronological
splits with zero future leakage. Compares 7-day seasonal naive, previous-interval
persistence, training-set mean, and the EstateIQ SeasonalBaselineModel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.benchmarks.metrics_utils import calculate_forecasting_metrics
from src.intelligence.seasonal_baseline import SeasonalBaselineModel


@dataclass
class ForecastingBenchResult:
    """Holds structured outputs and plots data for forecasting evaluation."""
    metrics_table: pd.DataFrame
    per_building_metrics: pd.DataFrame
    y_true: np.ndarray
    predictions: Dict[str, np.ndarray]
    timestamps: List[str]
    buildings: List[str]
    train_end_timestamp: str
    test_start_timestamp: str
    sample_count: int
    train_sample_count: int
    horizon_description: str
    methodology_notes: str


class EnergyForecastingBenchmark:
    """Runs leakage-free chronological benchmarks for facility energy load forecasting."""

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seasonal_lag_days: int = 7,
        intervals_per_hour: int = 4,
    ):
        if not (0.1 < train_ratio < 0.95):
            raise ValueError(f"train_ratio must be in (0.1, 0.95), got {train_ratio}")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seasonal_lag = seasonal_lag_days * 24 * intervals_per_hour  # 672 for 15-min data
        self.intervals_per_hour = intervals_per_hour

    def run(
        self,
        df: pd.DataFrame,
        selected_buildings: Optional[List[str]] = None,
        max_test_samples_per_building: Optional[int] = None,
    ) -> ForecastingBenchResult:
        """Executes chronological forecasting benchmark across selected buildings.

        Args:
            df: Facility energy telemetry containing 'timestamp', 'building_id', 'electricity_kwh'.
            selected_buildings: List of building IDs to evaluate (default: all).
            max_test_samples_per_building: Optional cap on test samples for rapid benchmarking.

        Returns:
            ForecastingBenchResult with comparative metrics and prediction series.
        """
        required = {"timestamp", "building_id", "electricity_kwh"}
        if not required.issubset(df.columns):
            raise ValueError(f"Missing required columns. Expected {required}, found {df.columns}")

        df_work = df.sort_values(["building_id", "timestamp"]).reset_index(drop=True)
        if selected_buildings:
            df_work = df_work[df_work["building_id"].isin(selected_buildings)].reset_index(drop=True)

        if df_work.empty:
            raise ValueError("No data available for the selected buildings.")

        all_y_true: List[float] = []
        all_seasonal_naive: List[float] = []
        all_persistence: List[float] = []
        all_train_mean: List[float] = []
        all_dif_baseline: List[float] = []
        all_timestamps: List[str] = []
        all_buildings: List[str] = []

        per_bld_records: List[Dict[str, Any]] = []
        train_counts = 0
        train_ends = []
        test_starts = []

        for bld_id, b_group in df_work.groupby("building_id", sort=False):
            vals = pd.to_numeric(b_group["electricity_kwh"], errors="coerce").to_numpy(dtype=float)
            stamps = b_group["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()
            total_n = len(vals)

            train_cutoff = int(total_n * self.train_ratio)
            # Test split starts at (1 - test_ratio)
            test_start_idx = int(total_n * (1.0 - self.test_ratio))
            test_start_idx = max(test_start_idx, self.seasonal_lag)

            if test_start_idx >= total_n:
                continue

            train_vals = vals[:train_cutoff]
            train_stamps = stamps[:train_cutoff]
            train_counts += len(train_vals)
            train_ends.append(train_stamps[-1])
            test_starts.append(stamps[test_start_idx])

            # 1. Fit EstateIQ Seasonal Baseline on Training Slice Only
            train_df = b_group.iloc[:train_cutoff][["timestamp", "building_id", "electricity_kwh"]].copy()
            baseline_model = SeasonalBaselineModel(min_observations=2).fit(train_df)

            # 2. Historical Training Mean
            train_mean_val = float(np.nanmean(train_vals)) if len(train_vals) > 0 else 0.0

            # 3. Test Slice
            test_indices = range(test_start_idx, total_n)
            if max_test_samples_per_building:
                test_indices = list(test_indices)[:max_test_samples_per_building]

            bld_y_true: List[float] = []
            bld_seasonal: List[float] = []
            bld_persist: List[float] = []
            bld_mean: List[float] = []
            bld_dif: List[float] = []

            for idx in test_indices:
                target = vals[idx]
                prev = vals[idx - 1]
                seasonal = vals[idx - self.seasonal_lag] if idx >= self.seasonal_lag else prev

                # DIF model profile lookup
                ts_str = stamps[idx]
                est = baseline_model.predict(bld_id, ts_str)
                dif_pred = est.expected_kwh if est else train_mean_val

                if np.isfinite(target) and np.isfinite(seasonal) and np.isfinite(prev):
                    bld_y_true.append(target)
                    bld_seasonal.append(seasonal)
                    bld_persist.append(prev)
                    bld_mean.append(train_mean_val)
                    bld_dif.append(dif_pred)
                    all_timestamps.append(ts_str)
                    all_buildings.append(bld_id)

            all_y_true.extend(bld_y_true)
            all_seasonal_naive.extend(bld_seasonal)
            all_persistence.extend(bld_persist)
            all_train_mean.extend(bld_mean)
            all_dif_baseline.extend(bld_dif)

            # Per-building metrics
            if bld_y_true:
                m_seas = calculate_forecasting_metrics(bld_y_true, bld_seasonal)
                m_pers = calculate_forecasting_metrics(bld_y_true, bld_persist)
                m_dif = calculate_forecasting_metrics(bld_y_true, bld_dif)
                per_bld_records.append({
                    "building_id": bld_id,
                    "samples": len(bld_y_true),
                    "7d_seasonal_mae": m_seas["mae"],
                    "7d_seasonal_r2": m_seas["r2"],
                    "persistence_mae": m_pers["mae"],
                    "persistence_r2": m_pers["r2"],
                    "dif_profile_mae": m_dif["mae"],
                    "dif_profile_r2": m_dif["r2"],
                })

        y_true_arr = np.asarray(all_y_true, dtype=float)
        preds_dict = {
            "7-Day Seasonal-Naive (Lag 672)": np.asarray(all_seasonal_naive, dtype=float),
            "Previous-Interval Persistence (Lag 1)": np.asarray(all_persistence, dtype=float),
            "Training-Set Historical Mean": np.asarray(all_train_mean, dtype=float),
            "EstateIQ Seasonal Baseline Profile": np.asarray(all_dif_baseline, dtype=float),
        }

        # Overall Metrics Table
        summary_rows = []
        for model_name, p_arr in preds_dict.items():
            m = calculate_forecasting_metrics(y_true_arr, p_arr)
            summary_rows.append({
                "Algorithm": model_name,
                "MAE (kWh)": m["mae"],
                "RMSE (kWh)": m["rmse"],
                "R² Score": m["r2"],
                "MAPE (%)": m["mape"],
                "Max Absolute Error (kWh)": m["max_error"],
                "Evaluation Samples": m["sample_count"],
            })

        metrics_df = pd.DataFrame(summary_rows).sort_values("MAE (kWh)").reset_index(drop=True)
        per_bld_df = pd.DataFrame(per_bld_records)

        horizon_desc = (
            "15-Minute Rolling Horizon: "
            "7-Day Seasonal-Naive uses the matching 15-minute slot from exactly 7 days prior (lag = 672 steps). "
            "Previous-Interval Persistence uses step t-1 (15-min horizon). "
            "Historical Mean predicts the static mean of the training set. "
            "EstateIQ Baseline queries the pre-fitted seasonal median profile for the corresponding weekday quarter."
        )

        methodology_notes = (
            "Strict chronological split (70% train / 15% validation / 15% test). "
            "No test set observations or future data were available during baseline profile fitting or thresholding. "
            "Near-zero energy readings (< 0.5 kWh) are masked out of the MAPE denominator to avoid division distortion."
        )

        return ForecastingBenchResult(
            metrics_table=metrics_df,
            per_building_metrics=per_bld_df,
            y_true=y_true_arr,
            predictions=preds_dict,
            timestamps=all_timestamps,
            buildings=all_buildings,
            train_end_timestamp=max(train_ends) if train_ends else "",
            test_start_timestamp=min(test_starts) if test_starts else "",
            sample_count=len(y_true_arr),
            train_sample_count=train_counts,
            horizon_description=horizon_desc,
            methodology_notes=methodology_notes,
        )

