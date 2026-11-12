"""Anomaly detection benchmark engine.

Compares EstateIQ-DIF (pointwise and persistence-gated) against standard baselines:
Seasonal Gaussian (Mean + std), Rolling 7-day Z-score, Static P99 Percentile,
and DIF ablations (Residual-only, Rules-only). Evaluates both interval-level
and event-level performance with leakage-free chronological training.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.benchmarks.metrics_utils import (
    calculate_classification_metrics,
    calculate_event_level_metrics,
)
from src.intelligence.config import DIFConfig
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.types import EventData


@dataclass
class AnomalyAlgorithmOutput:
    """Raw predictions and scores for one evaluated algorithm."""
    algorithm_name: str
    y_pred: np.ndarray
    y_scores: Optional[np.ndarray]
    metrics: Dict[str, Any]
    event_metrics: Dict[str, Any]


@dataclass
class AnomalyBenchResult:
    """Complete anomaly detection benchmark results across all candidate algorithms."""
    metrics_table: pd.DataFrame
    algorithm_outputs: Dict[str, AnomalyAlgorithmOutput]
    y_true: np.ndarray
    timestamps: List[str]
    buildings: List[str]
    sample_count: int
    positive_count: int
    episode_count: int
    evaluation_mode: str
    threshold_used: float
    provenance_badge: str
    methodology_notes: str


class AnomalyDetectionBenchmark:
    """Executes fair, leakage-free anomaly detection benchmarks on facility telemetry."""

    def __init__(
        self,
        default_threshold: float = 55.0,
        gaussian_k: float = 2.5,
        zscore_threshold: float = 3.0,
        percentile_threshold: float = 99.0,
        min_persistence_streak: int = 2,
    ):
        self.default_threshold = default_threshold
        self.gaussian_k = gaussian_k
        self.zscore_threshold = zscore_threshold
        self.percentile_threshold = percentile_threshold
        self.min_persistence_streak = min_persistence_streak

    def find_anomaly_episodes(self, df: pd.DataFrame) -> List[Tuple[str, pd.Timestamp, pd.Timestamp]]:
        """Identifies contiguous ground-truth anomaly episodes in the dataset."""
        if "anomaly_flag" not in df.columns:
            return []
        labeled = df[pd.to_numeric(df["anomaly_flag"], errors="coerce").fillna(0).astype(int) == 1].copy()
        if labeled.empty:
            return []
        episodes: List[Tuple[str, pd.Timestamp, pd.Timestamp]] = []
        for bld, group in labeled.groupby("building_id", sort=False):
            grp = group.sort_values("timestamp")
            cut = grp["timestamp"].diff().gt(pd.Timedelta(minutes=30)).fillna(True)
            for _, ep in grp.groupby(cut.cumsum()):
                episodes.append((str(bld), ep["timestamp"].min(), ep["timestamp"].max()))
        return episodes

    def run(
        self,
        df: pd.DataFrame,
        mode: str = "episodes",  # "episodes" or "full_test"
        selected_buildings: Optional[List[str]] = None,
        test_ratio: float = 0.15,
        threshold: Optional[float] = None,
        enable_ablations: bool = True,
    ) -> AnomalyBenchResult:
        """Runs anomaly detection comparison across candidate models.

        Args:
            df: Facility telemetry with 'timestamp', 'building_id', 'electricity_kwh', 'anomaly_flag'.
            mode: 'episodes' evaluates ±24h around labeled ground-truth episodes.
                  'full_test' evaluates the entire chronological test split.
            selected_buildings: Optional filter for specific buildings.
            test_ratio: Ratio for test split if mode == 'full_test'.
            threshold: Custom threshold for DIF (defaults to 55.0).
            enable_ablations: Whether to include DIF Residual-Only and Rules-Only ablations.

        Returns:
            AnomalyBenchResult containing metrics tables, confusion matrices, and ROC data.
        """
        thresh = threshold if threshold is not None else self.default_threshold
        required = {"timestamp", "building_id", "electricity_kwh", "anomaly_flag"}
        if not required.issubset(df.columns):
            raise ValueError(f"Missing required columns for anomaly benchmark. Expected {required}, found {df.columns}")

        df_work = df.sort_values(["building_id", "timestamp"]).reset_index(drop=True)
        if selected_buildings:
            df_work = df_work[df_work["building_id"].isin(selected_buildings)].reset_index(drop=True)

        if mode == "episodes":
            return self._run_episodes_mode(df_work, thresh, enable_ablations)
        else:
            return self._run_full_test_mode(df_work, thresh, test_ratio, enable_ablations)

    def _run_episodes_mode(
        self,
        df: pd.DataFrame,
        threshold: float,
        enable_ablations: bool,
    ) -> AnomalyBenchResult:
        """Evaluates strictly on ±24h windows around labeled anomaly episodes."""
        episodes = self.find_anomaly_episodes(df)
        if not episodes:
            raise ValueError("No ground-truth anomaly episodes found in the dataset.")

        y_true_list: List[int] = []
        timestamps_list: List[str] = []
        buildings_list: List[str] = []

        # Model score and prediction accumulators
        dif_scores: List[float] = []
        dif_preds: List[int] = []
        dif_persist_preds: List[int] = []

        gauss_scores: List[float] = []
        gauss_preds: List[int] = []

        zscore_scores: List[float] = []
        zscore_preds: List[int] = []

        p99_scores: List[float] = []
        p99_preds: List[int] = []

        # Ablation accumulators
        resid_only_scores: List[float] = []
        resid_only_preds: List[int] = []
        rules_only_scores: List[float] = []
        rules_only_preds: List[int] = []

        for bld, ep_start, ep_end in episodes:
            # Training history strictly precedes the episode
            history = df[(df["building_id"] == bld) & (df["timestamp"] < ep_start)].copy()
            if len(history) < 200:
                continue

            # 1. Fit EstateIQ-DIF Baseline Model
            try:
                dif_profile = SeasonalBaselineModel(min_observations=2).fit(history)
            except ValueError:
                continue

            # 2. Fit Gaussian Slot Baseline (Mean & Std per weekday slot)
            slot_stats: Dict[Tuple[int, int, int], Tuple[float, float]] = {}
            hist_ts = history["timestamp"]
            hist_dow = hist_ts.dt.dayofweek
            hist_hour = hist_ts.dt.hour
            hist_quarter = (hist_ts.dt.minute // 15) * 15
            hist_clean = pd.DataFrame({
                "dow": hist_dow, "hour": hist_hour, "quarter": hist_quarter,
                "energy": pd.to_numeric(history["electricity_kwh"], errors="coerce")
            }).dropna()

            for key, grp in hist_clean.groupby(["dow", "hour", "quarter"]):
                vals = grp["energy"].to_numpy()
                if len(vals) >= 2:
                    slot_stats[(key[0], key[1], key[2])] = (float(np.mean(vals)), max(float(np.std(vals)), 0.1))

            # 3. Fit P99 Threshold on Training Slice
            train_clean_vals = hist_clean["energy"].to_numpy()
            p99_thresh = float(np.percentile(train_clean_vals, self.percentile_threshold)) if len(train_clean_vals) else 100.0

            # 4. Evaluation Window: ±24h around the episode
            eval_window = df[
                (df["building_id"] == bld)
                & (df["timestamp"] >= ep_start - pd.Timedelta(hours=24))
                & (df["timestamp"] <= ep_end + pd.Timedelta(hours=24))
            ].copy()

            # Instantiate DIF Engines
            dif_cfg = DIFConfig()
            dif_cfg.anomaly_score_threshold = threshold
            dif_engine = EstateIQDIF(config=dif_cfg, baseline_model=dif_profile)

            # Ablation engines
            cfg_resid = DIFConfig(weight_contextual_residual=1.0, weight_domain_rules=0.0)
            cfg_resid.anomaly_score_threshold = threshold
            engine_resid = EstateIQDIF(config=cfg_resid, baseline_model=dif_profile)

            cfg_rules = DIFConfig(weight_contextual_residual=0.0, weight_domain_rules=1.0)
            cfg_rules.anomaly_score_threshold = threshold
            engine_rules = EstateIQDIF(config=cfg_rules, baseline_model=dif_profile)

            # Chronological Evaluation
            rolling_buffer = history["electricity_kwh"].dropna().tolist()[-672:]
            persistence_streak = 0
            prev_event_time: Optional[pd.Timestamp] = None

            for idx, row in enumerate(eval_window.itertuples(index=False)):
                stamp = pd.Timestamp(row.timestamp)
                act_kwh = float(row.electricity_kwh) if pd.notna(row.electricity_kwh) else 0.0
                truth = int(row.anomaly_flag) if pd.notna(row.anomaly_flag) else 0

                event = EventData(
                    event_id=f"ANOM-{bld}-{idx}", facility_id="FAC_CAMPUS",
                    building_id=str(bld), timestamp=stamp.isoformat(),
                    actual_kwh=act_kwh, hour=int(stamp.hour),
                    day_of_week=int(stamp.dayofweek), occupancy=0, temperature=24.0,
                    hvac_load=float(getattr(row, "hvac_kwh", 0.0) or 0.0),
                    extra_features={"power_factor": getattr(row, "power_factor", 0.95)},
                    interval_hours=0.25,
                )

                # A. Full EstateIQ-DIF
                dif_res = dif_engine.analyze(event)
                score = float(dif_res.anomaly.anomaly_score)
                is_raw_dif = int(score >= threshold)

                # Persistence gate (n >= min_persistence_streak)
                if prev_event_time and (stamp - prev_event_time).total_seconds() / 60.0 <= dif_cfg.persistence_max_gap_minutes:
                    persistence_streak = persistence_streak + 1 if is_raw_dif else 0
                else:
                    persistence_streak = 1 if is_raw_dif else 0
                prev_event_time = stamp

                is_persist_dif = int(persistence_streak >= self.min_persistence_streak)

                # B. Gaussian Baseline
                slot_key = (int(stamp.dayofweek), int(stamp.hour), int((stamp.minute // 15) * 15))
                g_mean, g_std = slot_stats.get(slot_key, (train_clean_vals.mean(), max(train_clean_vals.std(), 0.1)))
                g_z = abs(act_kwh - g_mean) / max(g_std, 1e-4)
                g_score = 100.0 * (1.0 - math.exp(-g_z / 3.0))
                g_pred = int(g_z >= self.gaussian_k)

                # C. Rolling 7-Day Z-Score
                if len(rolling_buffer) >= 96:
                    r_mean = float(np.mean(rolling_buffer))
                    r_std = float(max(np.std(rolling_buffer), 0.1))
                    r_z = abs(act_kwh - r_mean) / r_std
                    r_score = 100.0 * (1.0 - math.exp(-r_z / 3.0))
                    r_pred = int(r_z >= self.zscore_threshold)
                else:
                    r_score = 0.0
                    r_pred = 0
                rolling_buffer.append(act_kwh)
                if len(rolling_buffer) > 672:
                    rolling_buffer.pop(0)

                # D. Static P99
                p99_score = min(100.0, max(0.0, (act_kwh / max(p99_thresh, 1e-4)) * 100.0))
                p99_pred = int(act_kwh > p99_thresh)

                # E. Ablations
                if enable_ablations:
                    res_resid = engine_resid.analyze(event)
                    score_resid = float(res_resid.anomaly.anomaly_score)
                    resid_only_scores.append(score_resid)
                    resid_only_preds.append(int(score_resid >= threshold))

                    res_rules = engine_rules.analyze(event)
                    score_rules = float(res_rules.anomaly.anomaly_score)
                    rules_only_scores.append(score_rules)
                    rules_only_preds.append(int(score_rules >= threshold))

                y_true_list.append(truth)
                timestamps_list.append(stamp.isoformat())
                buildings_list.append(str(bld))

                dif_scores.append(score)
                dif_preds.append(is_raw_dif)
                dif_persist_preds.append(is_persist_dif)

                gauss_scores.append(g_score)
                gauss_preds.append(g_pred)

                zscore_scores.append(r_score)
                zscore_preds.append(r_pred)

                p99_scores.append(p99_score)
                p99_preds.append(p99_pred)

        y_true = np.asarray(y_true_list, dtype=int)
        if len(y_true) == 0:
            raise ValueError("No samples were evaluated in the anomaly benchmark.")

        # Candidate algorithms dictionary
        algorithms: Dict[str, Tuple[np.ndarray, Optional[np.ndarray]]] = {
            "EstateIQ-DIF (Pointwise, Thresh=55)": (np.asarray(dif_preds, dtype=int), np.asarray(dif_scores, dtype=float)),
            "EstateIQ-DIF (Persistence Gated, n>=2)": (np.asarray(dif_persist_preds, dtype=int), np.asarray(dif_scores, dtype=float)),
            "Seasonal Gaussian Baseline (μ ± 2.5σ)": (np.asarray(gauss_preds, dtype=int), np.asarray(gauss_scores, dtype=float)),
            "Rolling 7-Day Z-Score (z >= 3.0)": (np.asarray(zscore_preds, dtype=int), np.asarray(zscore_scores, dtype=float)),
            "Static Historical Percentile (P99)": (np.asarray(p99_preds, dtype=int), np.asarray(p99_scores, dtype=float)),
        }

        if enable_ablations:
            algorithms["EstateIQ-DIF (Ablation: Residual-Only)"] = (np.asarray(resid_only_preds, dtype=int), np.asarray(resid_only_scores, dtype=float))
            algorithms["EstateIQ-DIF (Ablation: Domain-Rules-Only)"] = (np.asarray(rules_only_preds, dtype=int), np.asarray(rules_only_scores, dtype=float))

        outputs: Dict[str, AnomalyAlgorithmOutput] = {}
        summary_rows: List[Dict[str, Any]] = []

        for name, (preds_arr, scores_arr) in algorithms.items():
            metrics = calculate_classification_metrics(y_true, preds_arr, scores_arr)
            event_m = calculate_event_level_metrics(timestamps_list, y_true, preds_arr)
            outputs[name] = AnomalyAlgorithmOutput(
                algorithm_name=name,
                y_pred=preds_arr,
                y_scores=scores_arr,
                metrics=metrics,
                event_metrics=event_m,
            )
            cm = metrics["confusion_matrix"]
            summary_rows.append({
                "Algorithm": name,
                "Precision": metrics["precision"],
                "Recall (Sensitivity)": metrics["recall"],
                "F1-Score": metrics["f1_score"],
                "Balanced Accuracy": metrics["balanced_accuracy"],
                "ROC-AUC": metrics["roc_auc"],
                "PR-AUC": metrics["pr_auc"],
                "False-Positive Rate": metrics["false_positive_rate"],
                "Raw Accuracy": metrics["accuracy"],
                "TP": cm["tp"],
                "FP": cm["fp"],
                "TN": cm["tn"],
                "FN": cm["fn"],
                "Event Detection Rate": event_m["event_detection_rate"],
                "Mean Delay (min)": event_m["mean_detection_delay_minutes"],
            })

        metrics_df = pd.DataFrame(summary_rows).sort_values("F1-Score", ascending=False).reset_index(drop=True)

        return AnomalyBenchResult(
            metrics_table=metrics_df,
            algorithm_outputs=outputs,
            y_true=y_true,
            timestamps=timestamps_list,
            buildings=buildings_list,
            sample_count=len(y_true),
            positive_count=int(np.sum(y_true == 1)),
            episode_count=len(episodes),
            evaluation_mode="INJECTED_EPISODES_BUFFER_24H",
            threshold_used=threshold,
            provenance_badge="[SYNTHETIC INJECTED EPISODES — AUDIT GROUND TRUTH]",
            methodology_notes=(
                "Evaluates candidate classifiers on labeled ground truth episodes (BLD003 HVAC fault, BLD001 after-hours usage) "
                "with a ±24-hour baseline window. Training history strictly precedes each episode. "
                "Precision, Recall, F1, and PR-AUC are the primary evaluation metrics due to heavy class imbalance."
            ),
        )

    def _run_full_test_mode(
        self,
        df: pd.DataFrame,
        threshold: float,
        test_ratio: float,
        enable_ablations: bool,
    ) -> AnomalyBenchResult:
        """Evaluates on the entire chronological test split across all selected buildings."""
        y_true_list: List[int] = []
        timestamps_list: List[str] = []
        buildings_list: List[str] = []

        dif_scores: List[float] = []
        dif_preds: List[int] = []
        dif_persist_preds: List[int] = []

        gauss_scores: List[float] = []
        gauss_preds: List[int] = []

        zscore_scores: List[float] = []
        zscore_preds: List[int] = []

        p99_scores: List[float] = []
        p99_preds: List[int] = []

        resid_only_scores: List[float] = []
        resid_only_preds: List[int] = []
        rules_only_scores: List[float] = []
        rules_only_preds: List[int] = []

        for bld, group in df.groupby("building_id", sort=False):
            total_n = len(group)
            cutoff = int(total_n * (1.0 - test_ratio))
            if cutoff >= total_n or cutoff < 100:
                continue

            history = group.iloc[:cutoff].copy()
            test_slice = group.iloc[cutoff:].copy()

            try:
                dif_profile = SeasonalBaselineModel(min_observations=2).fit(history)
            except ValueError:
                continue

            # Gaussian slot stats
            slot_stats: Dict[Tuple[int, int, int], Tuple[float, float]] = {}
            hist_ts = history["timestamp"]
            hist_clean = pd.DataFrame({
                "dow": hist_ts.dt.dayofweek, "hour": hist_ts.dt.hour,
                "quarter": (hist_ts.dt.minute // 15) * 15,
                "energy": pd.to_numeric(history["electricity_kwh"], errors="coerce")
            }).dropna()

            for key, grp in hist_clean.groupby(["dow", "hour", "quarter"]):
                vals = grp["energy"].to_numpy()
                if len(vals) >= 2:
                    slot_stats[(key[0], key[1], key[2])] = (float(np.mean(vals)), max(float(np.std(vals)), 0.1))

            train_clean_vals = hist_clean["energy"].to_numpy()
            p99_thresh = float(np.percentile(train_clean_vals, self.percentile_threshold)) if len(train_clean_vals) else 100.0

            dif_cfg = DIFConfig(anomaly_score_threshold=threshold)
            dif_engine = EstateIQDIF(config=dif_cfg, baseline_model=dif_profile)

            cfg_resid = DIFConfig(weight_contextual_residual=1.0, weight_domain_rules=0.0, anomaly_score_threshold=threshold)
            engine_resid = EstateIQDIF(config=cfg_resid, baseline_model=dif_profile)

            cfg_rules = DIFConfig(weight_contextual_residual=0.0, weight_domain_rules=1.0, anomaly_score_threshold=threshold)
            engine_rules = EstateIQDIF(config=cfg_rules, baseline_model=dif_profile)

            rolling_buffer = history["electricity_kwh"].dropna().tolist()[-672:]
            persistence_streak = 0
            prev_event_time: Optional[pd.Timestamp] = None

            for idx, row in enumerate(test_slice.itertuples(index=False)):
                stamp = pd.Timestamp(row.timestamp)
                act_kwh = float(row.electricity_kwh) if pd.notna(row.electricity_kwh) else 0.0
                truth = int(row.anomaly_flag) if pd.notna(row.anomaly_flag) else 0

                event = EventData(
                    event_id=f"FULL-TEST-{bld}-{idx}", facility_id="FAC_CAMPUS",
                    building_id=str(bld), timestamp=stamp.isoformat(),
                    actual_kwh=act_kwh, hour=int(stamp.hour),
                    day_of_week=int(stamp.dayofweek), occupancy=0, temperature=24.0,
                    hvac_load=float(getattr(row, "hvac_kwh", 0.0) or 0.0),
                    extra_features={"power_factor": getattr(row, "power_factor", 0.95)},
                    interval_hours=0.25,
                )

                dif_res = dif_engine.analyze(event)
                score = float(dif_res.anomaly.anomaly_score)
                is_raw_dif = int(score >= threshold)

                if prev_event_time and (stamp - prev_event_time).total_seconds() / 60.0 <= dif_cfg.persistence_max_gap_minutes:
                    persistence_streak = persistence_streak + 1 if is_raw_dif else 0
                else:
                    persistence_streak = 1 if is_raw_dif else 0
                prev_event_time = stamp
                is_persist_dif = int(persistence_streak >= self.min_persistence_streak)

                # Gaussian
                slot_key = (int(stamp.dayofweek), int(stamp.hour), int((stamp.minute // 15) * 15))
                g_mean, g_std = slot_stats.get(slot_key, (train_clean_vals.mean(), max(train_clean_vals.std(), 0.1)))
                g_z = abs(act_kwh - g_mean) / max(g_std, 1e-4)
                g_score = 100.0 * (1.0 - math.exp(-g_z / 3.0))
                g_pred = int(g_z >= self.gaussian_k)

                # Rolling Z
                if len(rolling_buffer) >= 96:
                    r_mean = float(np.mean(rolling_buffer))
                    r_std = float(max(np.std(rolling_buffer), 0.1))
                    r_z = abs(act_kwh - r_mean) / r_std
                    r_score = 100.0 * (1.0 - math.exp(-r_z / 3.0))
                    r_pred = int(r_z >= self.zscore_threshold)
                else:
                    r_score = 0.0
                    r_pred = 0
                rolling_buffer.append(act_kwh)
                if len(rolling_buffer) > 672:
                    rolling_buffer.pop(0)

                # P99
                p99_score = min(100.0, max(0.0, (act_kwh / max(p99_thresh, 1e-4)) * 100.0))
                p99_pred = int(act_kwh > p99_thresh)

                if enable_ablations:
                    res_resid = engine_resid.analyze(event)
                    score_resid = float(res_resid.anomaly.anomaly_score)
                    resid_only_scores.append(score_resid)
                    resid_only_preds.append(int(score_resid >= threshold))

                    res_rules = engine_rules.analyze(event)
                    score_rules = float(res_rules.anomaly.anomaly_score)
                    rules_only_scores.append(score_rules)
                    rules_only_preds.append(int(score_rules >= threshold))

                y_true_list.append(truth)
                timestamps_list.append(stamp.isoformat())
                buildings_list.append(str(bld))

                dif_scores.append(score)
                dif_preds.append(is_raw_dif)
                dif_persist_preds.append(is_persist_dif)

                gauss_scores.append(g_score)
                gauss_preds.append(g_pred)

                zscore_scores.append(r_score)
                zscore_preds.append(r_pred)

                p99_scores.append(p99_score)
                p99_preds.append(p99_pred)

        y_true = np.asarray(y_true_list, dtype=int)
        algorithms = {
            "EstateIQ-DIF (Pointwise, Thresh=55)": (np.asarray(dif_preds, dtype=int), np.asarray(dif_scores, dtype=float)),
            "EstateIQ-DIF (Persistence Gated, n>=2)": (np.asarray(dif_persist_preds, dtype=int), np.asarray(dif_scores, dtype=float)),
            "Seasonal Gaussian Baseline (μ ± 2.5σ)": (np.asarray(gauss_preds, dtype=int), np.asarray(gauss_scores, dtype=float)),
            "Rolling 7-Day Z-Score (z >= 3.0)": (np.asarray(zscore_preds, dtype=int), np.asarray(zscore_scores, dtype=float)),
            "Static Historical Percentile (P99)": (np.asarray(p99_preds, dtype=int), np.asarray(p99_scores, dtype=float)),
        }
        if enable_ablations:
            algorithms["EstateIQ-DIF (Ablation: Residual-Only)"] = (np.asarray(resid_only_preds, dtype=int), np.asarray(resid_only_scores, dtype=float))
            algorithms["EstateIQ-DIF (Ablation: Domain-Rules-Only)"] = (np.asarray(rules_only_preds, dtype=int), np.asarray(rules_only_scores, dtype=float))

        outputs = {}
        summary_rows = []
        for name, (preds_arr, scores_arr) in algorithms.items():
            metrics = calculate_classification_metrics(y_true, preds_arr, scores_arr)
            event_m = calculate_event_level_metrics(timestamps_list, y_true, preds_arr)
            outputs[name] = AnomalyAlgorithmOutput(
                algorithm_name=name, y_pred=preds_arr, y_scores=scores_arr,
                metrics=metrics, event_metrics=event_m,
            )
            cm = metrics["confusion_matrix"]
            summary_rows.append({
                "Algorithm": name,
                "Precision": metrics["precision"],
                "Recall (Sensitivity)": metrics["recall"],
                "F1-Score": metrics["f1_score"],
                "Balanced Accuracy": metrics["balanced_accuracy"],
                "ROC-AUC": metrics["roc_auc"],
                "PR-AUC": metrics["pr_auc"],
                "False-Positive Rate": metrics["false_positive_rate"],
                "Raw Accuracy": metrics["accuracy"],
                "TP": cm["tp"], "FP": cm["fp"], "TN": cm["tn"], "FN": cm["fn"],
                "Event Detection Rate": event_m["event_detection_rate"],
                "Mean Delay (min)": event_m["mean_detection_delay_minutes"],
            })

        metrics_df = pd.DataFrame(summary_rows).sort_values("F1-Score", ascending=False).reset_index(drop=True)

        return AnomalyBenchResult(
            metrics_table=metrics_df,
            algorithm_outputs=outputs,
            y_true=y_true,
            timestamps=timestamps_list,
            buildings=buildings_list,
            sample_count=len(y_true),
            positive_count=int(np.sum(y_true == 1)),
            episode_count=0,
            evaluation_mode=f"FULL_CHRONOLOGICAL_TEST_SPLIT_{int(test_ratio*100)}PCT",
            threshold_used=threshold,
            provenance_badge="[SYNTHETIC TEST SPLIT — EVALUATION GROUND TRUTH]",
            methodology_notes=(
                f"Evaluates candidate classifiers on the final {int(test_ratio*100)}% chronological test split. "
                "Training baseline profiles fit strictly on preceding data with zero test leakage."
            ),
        )

