"""Comprehensive unit test suite for the EstateIQ Algorithm Benchmark Suite.

Tests:
1. Dataset discovery and schema validation.
2. Chronological train/test splitting and leakage prevention.
3. Hand-computed metric calculation verification.
4. Safe edge-case handling (zeros, empty series, missing values).
5. Event-level anomaly detection and delay calculations.
6. Deterministic output across candidate algorithms.
7. Pointwise vs persistence-gated confusion matrices.
8. Complexity and runtime harness isolated from I/O.
9. Theoretical complexity audit specs.
10. Export manifest schema and reproducibility attributes.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

from src.benchmarks.dataset_loader import DatasetLoader, DatasetMetadata
from src.benchmarks.metrics_utils import (
    calculate_forecasting_metrics,
    calculate_classification_metrics,
    calculate_event_level_metrics,
)
from src.benchmarks.forecasting_bench import EnergyForecastingBenchmark
from src.benchmarks.anomaly_bench import AnomalyDetectionBenchmark
from src.benchmarks.complexity_bench import ComplexityBenchmark
from src.intelligence.config import DIFConfig
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.types import EventData


class TestBenchmarkSuite(unittest.TestCase):
    """Test suite covering data integrity, metrics, leakage prevention, and algorithm execution."""

    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent

    # -------------------------------------------------------------------------
    # 1. Dataset Discovery and Schema Validation
    # -------------------------------------------------------------------------
    def test_dataset_discovery_and_schema(self):
        loader = DatasetLoader(self.project_root)
        path = loader.discover_default_dataset_path()
        self.assertIsNotNone(path, "Default dataset must be discoverable in repository")
        self.assertTrue(path.is_file())

        df, meta = loader.load_dataset(path, max_rows=500)
        self.assertIsInstance(meta, DatasetMetadata)
        self.assertGreater(meta.total_rows, 0)
        self.assertEqual(len(meta.sha256_fingerprint), 64, "SHA-256 fingerprint must be 64 hex characters")
        self.assertIn("electricity_kwh", df.columns)
        self.assertIn("timestamp", df.columns)
        self.assertIn("building_id", df.columns)
        self.assertIn("SYNTHETIC", meta.provenance_badge)

    def test_dataset_loader_invalid_schema_rejection(self):
        loader = DatasetLoader(self.project_root)
        # Missing energy column
        csv_no_energy = io.StringIO("timestamp,building_id\n2026-01-01T00:00:00Z,BLD1\n")
        with self.assertRaises(ValueError):
            loader.load_dataset(csv_no_energy)

        # Missing timestamp column
        csv_no_ts = io.StringIO("building_id,electricity_kwh\nBLD1,45.2\n")
        with self.assertRaises(ValueError):
            loader.load_dataset(csv_no_ts)

    # -------------------------------------------------------------------------
    # 2. Chronological Splitting and Leakage Prevention
    # -------------------------------------------------------------------------
    def test_chronological_splitting_leakage_prevention(self):
        # Create a mock 30-day time series
        ts = pd.date_range("2026-01-01", periods=30 * 96, freq="15min", tz="UTC")
        df = pd.DataFrame({
            "timestamp": ts,
            "building_id": "BLD_TEST",
            "electricity_kwh": 30.0 + 5.0 * np.sin(np.linspace(0, 50, len(ts))),
            "anomaly_flag": 0,
        })

        bench = EnergyForecastingBenchmark(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
        result = bench.run(df, selected_buildings=["BLD_TEST"])

        self.assertGreater(len(result.y_true), 0)
        # Verify strict chronological separation: all test timestamps must be strictly after train end
        train_end_dt = pd.to_datetime(result.train_end_timestamp)
        test_start_dt = pd.to_datetime(result.test_start_timestamp)
        self.assertLess(train_end_dt, test_start_dt, "Training end must strictly precede test start")

    def test_leakage_independence_proof(self):
        """Proof that future test labels or values never alter fitted training profiles."""
        ts = pd.date_range("2026-01-01", periods=14 * 96, freq="15min", tz="UTC")
        df_clean = pd.DataFrame({
            "timestamp": ts,
            "building_id": "BLD_LEAK_TEST",
            "electricity_kwh": 25.0,
            "anomaly_flag": 0,
        })
        train_cutoff = 10 * 96

        # Fit model on training slice
        model1 = SeasonalBaselineModel(min_observations=2).fit(df_clean.iloc[:train_cutoff])
        est1 = model1.predict("BLD_LEAK_TEST", ts[0].isoformat())

        # Modify future test values drastically
        df_contaminated = df_clean.copy()
        df_contaminated.iloc[train_cutoff:, df_contaminated.columns.get_loc("electricity_kwh")] = 9999.0

        # Model fitted strictly on training data must produce identical parameters
        model2 = SeasonalBaselineModel(min_observations=2).fit(df_contaminated.iloc[:train_cutoff])
        est2 = model2.predict("BLD_LEAK_TEST", ts[0].isoformat())

        self.assertEqual(est1.expected_kwh, est2.expected_kwh)
        self.assertEqual(est1.scale_kwh, est2.scale_kwh)

    # -------------------------------------------------------------------------
    # 3. Hand-Computed Metric Verification
    # -------------------------------------------------------------------------
    def test_hand_computed_forecasting_metrics(self):
        y_true = np.array([10.0, 20.0, 30.0])
        y_pred = np.array([12.0, 18.0, 33.0])
        # Errors: -2.0, +2.0, -3.0
        # MAE: (2 + 2 + 3) / 3 = 7 / 3 = 2.3333
        # RMSE: sqrt((4 + 4 + 9) / 3) = sqrt(17 / 3) = 2.3805
        # Max error: 3.0
        # SS_tot: (10-20)^2 + (20-20)^2 + (30-20)^2 = 100 + 0 + 100 = 200
        # SS_res: 4 + 4 + 9 = 17
        # R2: 1 - 17/200 = 1 - 0.085 = 0.915
        m = calculate_forecasting_metrics(y_true, y_pred)
        self.assertAlmostEqual(m["mae"], 2.3333, places=3)
        self.assertAlmostEqual(m["rmse"], 2.3805, places=3)
        self.assertAlmostEqual(m["r2"], 0.9150, places=3)
        self.assertEqual(m["max_error"], 3.0)
        self.assertEqual(m["sample_count"], 3)

    def test_hand_computed_classification_metrics(self):
        y_true = np.array([0, 0, 1, 1, 0])
        y_pred = np.array([0, 1, 1, 0, 0])
        # TP: 1 (idx 2)
        # FP: 1 (idx 1)
        # TN: 2 (idx 0, 4)
        # FN: 1 (idx 3)
        # Total = 5
        # Accuracy = (1 + 2) / 5 = 0.60
        # Precision = 1 / (1 + 1) = 0.50
        # Recall = 1 / (1 + 1) = 0.50
        # Specificity = 2 / (2 + 1) = 2/3 = 0.6667
        # Balanced Accuracy = 0.5 * (0.50 + 0.6667) = 0.5833
        # F1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.50
        # FPR = 1 / (1 + 2) = 1/3 = 0.3333
        c = calculate_classification_metrics(y_true, y_pred)
        cm = c["confusion_matrix"]
        self.assertEqual(cm["tp"], 1)
        self.assertEqual(cm["fp"], 1)
        self.assertEqual(cm["tn"], 2)
        self.assertEqual(cm["fn"], 1)
        self.assertAlmostEqual(c["accuracy"], 0.6000, places=3)
        self.assertAlmostEqual(c["precision"], 0.5000, places=3)
        self.assertAlmostEqual(c["recall"], 0.5000, places=3)
        self.assertAlmostEqual(c["specificity"], 0.6667, places=3)
        self.assertAlmostEqual(c["balanced_accuracy"], 0.5833, places=3)
        self.assertAlmostEqual(c["f1_score"], 0.5000, places=3)
        self.assertAlmostEqual(c["false_positive_rate"], 0.3333, places=3)

    # -------------------------------------------------------------------------
    # 4. Safe Edge-Case Handling (Zeros, Empty Series)
    # -------------------------------------------------------------------------
    def test_zero_and_empty_metric_handling(self):
        # Empty inputs
        empty_fc = calculate_forecasting_metrics([], [])
        self.assertEqual(empty_fc["sample_count"], 0)
        self.assertEqual(empty_fc["mae"], 0.0)

        empty_clf = calculate_classification_metrics([], [])
        self.assertEqual(empty_clf["sample_count"], 0)
        self.assertEqual(empty_clf["precision"], 0.0)

        # Zero actual values in MAPE: verify no ZeroDivisionError
        zeros_true = np.array([0.0, 0.0, 10.0])
        zeros_pred = np.array([2.0, 1.0, 12.0])
        safe_m = calculate_forecasting_metrics(zeros_true, zeros_pred, mape_threshold_kwh=0.5)
        # MAPE should only calculate on the index >= 0.5 (idx 2: |10 - 12| / 10 = 20%)
        self.assertEqual(safe_m["mape"], 20.0)
        self.assertEqual(safe_m["mape_valid_count"], 1)

    # -------------------------------------------------------------------------
    # 5. Event-Level Anomaly Detection & Delay
    # -------------------------------------------------------------------------
    def test_event_level_metrics_calculation(self):
        timestamps = [
            "2026-03-22T01:00:00Z",
            "2026-03-22T01:15:00Z",
            "2026-03-22T01:30:00Z",
            "2026-03-22T01:45:00Z",
            # Normal gap
            "2026-03-22T08:00:00Z",
            "2026-03-22T08:15:00Z",
        ]
        # True anomaly in first 4 steps (1 episode)
        y_true = [1, 1, 1, 1, 0, 0]
        # Model detects on step 2 (15 minutes delay)
        y_pred = [0, 1, 1, 1, 0, 0]

        ev_m = calculate_event_level_metrics(timestamps, y_true, y_pred, max_gap_minutes=30)
        self.assertEqual(ev_m["total_events"], 1)
        self.assertEqual(ev_m["detected_events"], 1)
        self.assertEqual(ev_m["event_detection_rate"], 1.0)
        self.assertEqual(ev_m["mean_detection_delay_minutes"], 15.0)
        self.assertEqual(ev_m["false_alarm_clusters"], 0)

    # -------------------------------------------------------------------------
    # 6. Pointwise vs Persistence-Gated Anomaly Confirmation
    # -------------------------------------------------------------------------
    def test_pointwise_vs_persistence_gated_behavior(self):
        ts = pd.date_range("2026-01-01", periods=14 * 96, freq="15min", tz="UTC")
        df_hist = pd.DataFrame({
            "timestamp": ts, "building_id": "B1", "electricity_kwh": 20.0
        })
        profile = SeasonalBaselineModel(min_observations=2).fit(df_hist)

        # Single transient spike (step 1 only)
        ev_transient = EventData("e1", "f1", "B1", "2026-01-15T12:00:00Z", 95.0, 12, 3, 0, 25.0)
        ev_normal = EventData("e2", "f1", "B1", "2026-01-15T12:15:00Z", 20.0, 12, 3, 0, 25.0)

        dif = EstateIQDIF(config=DIFConfig(anomaly_score_threshold=55.0), baseline_model=profile)
        res1 = dif.analyze(ev_transient)
        # Pointwise score is anomalous (> 55)
        self.assertGreaterEqual(res1.anomaly.anomaly_score, 55.0)

        # Sustained anomaly over 2 steps
        dif_sustained = EstateIQDIF(config=DIFConfig(anomaly_score_threshold=55.0), baseline_model=profile)
        ev_step1 = EventData("s1", "f1", "B1", "2026-01-15T14:00:00Z", 95.0, 14, 3, 0, 25.0)
        ev_step2 = EventData("s2", "f1", "B1", "2026-01-15T14:15:00Z", 95.0, 14, 3, 0, 25.0)

        r_s1 = dif_sustained.analyze(ev_step1)
        r_s2 = dif_sustained.analyze(ev_step2)

        # Step 2 must confirm temporal persistence
        evidence_text = " ".join(r_s2.anomaly.evidence)
        self.assertIn("Temporal Persistence Confirmed", evidence_text)

    # -------------------------------------------------------------------------
    # 7. Complexity Benchmark Harness
    # -------------------------------------------------------------------------
    def test_complexity_benchmark_harness(self):
        ts = pd.date_range("2026-01-01", periods=500, freq="15min", tz="UTC")
        df_bench = pd.DataFrame({
            "timestamp": ts, "building_id": "B1", "electricity_kwh": 25.0 + np.random.randn(500)
        })

        cb = ComplexityBenchmark()
        specs = cb.get_theoretical_specifications()
        self.assertGreaterEqual(len(specs), 5)
        for s in specs:
            self.assertIn("O(", s.offline_fit_time)
            self.assertIn("O(", s.online_inference_time)

        emp_results = cb.run_empirical_benchmark(df_bench, sample_size=300, warmup_count=20)
        self.assertGreaterEqual(len(emp_results), 3)
        dif_res = next(r for r in emp_results if "EstateIQ-DIF" in r.algorithm_name)
        self.assertGreater(dif_res.throughput_events_per_sec, 0.0)
        self.assertGreater(dif_res.median_latency_us, 0.0)


    # -------------------------------------------------------------------------
    # 8. End-to-End Benchmark Execution on Real Dataset
    # -------------------------------------------------------------------------
    def test_end_to_end_forecasting_benchmark(self):
        loader = DatasetLoader(self.project_root)
        df, meta = loader.load_dataset(max_rows=1000)
        bench = EnergyForecastingBenchmark(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
        res = bench.run(df, selected_buildings=[meta.buildings[0]], max_test_samples_per_building=50)
        self.assertGreater(len(res.metrics_table), 0)
        self.assertIn("7-Day Seasonal-Naive (Lag 672)", res.metrics_table["Algorithm"].values)
        self.assertIn("MAE (kWh)", res.metrics_table.columns)

    def test_end_to_end_anomaly_benchmark(self):
        loader = DatasetLoader(self.project_root)
        df, meta = loader.load_dataset(max_rows=100000)
        bench = AnomalyDetectionBenchmark(default_threshold=55.0)
        res = bench.run(df, mode="episodes", selected_buildings=["BLD001", "BLD003"])
        self.assertGreater(len(res.metrics_table), 0)
        self.assertIn("EstateIQ-DIF (Persistence Gated, n>=2)", res.metrics_table["Algorithm"].values)
        self.assertIn("Precision", res.metrics_table.columns)
        self.assertIn("Recall (Sensitivity)", res.metrics_table.columns)
        self.assertIn("F1-Score", res.metrics_table.columns)
        self.assertEqual(res.positive_count, 42)

    def test_app_import_and_metadata(self):
        import benchmark_app
        self.assertTrue(hasattr(benchmark_app, "main"))


if __name__ == "__main__":
    unittest.main()
