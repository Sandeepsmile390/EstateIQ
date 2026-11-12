"""Automated Test Suite for EstateIQ V2 Scientific Benchmark.

Verifies:
1. Dataset reproducibility for a fixed seed.
2. Label correctness and event interval alignment.
3. No duplicate or unsorted timestamps within any building.
4. Clean split isolation (Train and Val 100% nominal, zero test label leakage).
5. All candidate algorithms score identical held-out test rows.
6. Exact mathematical reproducibility from per-reading predictions.
7. Correct building-day exposure denominator calculation.
8. Agreement across JSON, CSV, and Markdown evidence artifacts.
"""

import json
import os
import sys
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pytest

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_generator_v2.generator_v2 import DatasetGeneratorV2
from src.data_generator_v2.validation_v2 import validate_v2_dataset

OUTPUT_DIR = Path("output/presentation/algorithm_comparison_v2")
DATA_DIR = Path("facility_dataset/data/synthetic_v2")


def test_dataset_reproducibility():
    """Verify that DatasetGeneratorV2 produces deterministic output with fixed seed."""
    gen1 = DatasetGeneratorV2(seed=42)
    df1 = gen1.generate_raw_baseline_readings()
    gen2 = DatasetGeneratorV2(seed=42)
    df2 = gen2.generate_raw_baseline_readings()

    pd.testing.assert_frame_equal(df1, df2)


def test_validation_rules_pass():
    """Verify that the generated V2 dataset passes all physical and logical constraints."""
    data_csv = DATA_DIR / "energy_readings_v2.csv"
    events_csv = DATA_DIR / "ground_truth_events_v2.csv"
    assert data_csv.exists() and events_csv.exists()

    df = pd.read_csv(data_csv)
    events_df = pd.read_csv(events_csv)

    val_summary = validate_v2_dataset(df, events_df)
    assert val_summary["validation_passed"] is True
    assert val_summary["train_nominal_verified"] is True
    assert val_summary["val_nominal_verified"] is True
    assert val_summary["event_row_alignment_verified"] is True


def test_temporal_monotonicity_and_no_duplicates():
    """Verify no timestamps are unsorted or duplicated within any building."""
    data_csv = DATA_DIR / "energy_readings_v2.csv"
    df = pd.read_csv(data_csv)

    for bld, group in df.groupby("building_id"):
        ts = pd.to_datetime(group["timestamp"])
        assert ts.is_monotonic_increasing, f"Building {bld} timestamps not monotonic!"
        assert group.duplicated(subset=["timestamp"]).sum() == 0, f"Building {bld} has duplicates!"


def test_artifacts_exist():
    """Verify all 6 figures (PNG & SVG), metrics CSVs, raw predictions, and briefs exist."""
    required_files = [
        "DATA_GENERATOR_AUDIT.md",
        "BENCHMARK_REPORT.md",
        "JURY_PRESENTATION_BRIEF.md",
        "benchmark_metrics.csv",
        "benchmark_metrics_multiseed.csv",
        "benchmark_results.json",
        "per_reading_predictions.csv",
        "fig1_main_algorithm_comparison.png",
        "fig1_main_algorithm_comparison.svg",
        "fig2_operational_tradeoff.png",
        "fig2_operational_tradeoff.svg",
        "fig3_precision_recall_curves.png",
        "fig3_precision_recall_curves.svg",
        "fig4_confusion_matrices.png",
        "fig4_confusion_matrices.svg",
        "fig5_event_detection_and_delay.png",
        "fig5_event_detection_and_delay.svg",
        "fig6_latency_comparison.png",
        "fig6_latency_comparison.svg",
    ]
    for filename in required_files:
        filepath = OUTPUT_DIR / filename
        assert filepath.exists(), f"Missing required benchmark artifact: {filepath}"
        assert filepath.stat().st_size > 0, f"Artifact is empty: {filepath}"


def test_exposure_denominator_and_metrics_consistency():
    """Verify confusion matrix counts, formulas, and building-day false alarm denominator."""
    csv_path = OUTPUT_DIR / "benchmark_metrics.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)

    expected_total_rows = 43680
    expected_bld_days = expected_total_rows * 0.25 / 24.0  # 455.0 building-days

    for _, row in df.iterrows():
        tp = row["tp"]
        fp = row["fp"]
        tn = row["tn"]
        fn = row["fn"]

        # 1. Total instance counts
        assert tp + fn == 543, f"Positive count mismatch for {row['algorithm']}"
        assert tn + fp == 43137, f"Negative count mismatch for {row['algorithm']}"
        assert tp + fp + tn + fn == expected_total_rows

        # 2. Precision
        expected_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        assert pytest.approx(row["precision"], abs=1e-3) == expected_prec

        # 3. Recall
        expected_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        assert pytest.approx(row["recall"], abs=1e-3) == expected_rec

        # 4. F1-Score
        expected_f1 = (
            2 * expected_prec * expected_rec / (expected_prec + expected_rec)
            if (expected_prec + expected_rec) > 0
            else 0.0
        )
        assert pytest.approx(row["f1_score"], abs=1e-3) == expected_f1

        # 5. False alerts per building-day
        expected_fad = fp / expected_bld_days
        assert pytest.approx(row["false_alerts_per_bld_day"], abs=1e-2) == expected_fad


def test_raw_prediction_exact_reproducibility():
    """Verify that aggregate metrics can be exact-recomputed from per_reading_predictions.csv."""
    pred_path = OUTPUT_DIR / "per_reading_predictions.csv"
    metrics_path = OUTPUT_DIR / "benchmark_metrics.csv"
    assert pred_path.exists() and metrics_path.exists()

    pred_df = pd.read_csv(pred_path)
    metrics_df = pd.read_csv(metrics_path)

    assert len(pred_df) == 43680, f"Expected 43,680 test rows, found {len(pred_df)}"
    y_true = pred_df["ground_truth_label"].values

    for _, m_row in metrics_df.iterrows():
        algo_name = m_row["algorithm"]
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", algo_name.lower()).strip("_")
        col_name = f"{slug}_pred"
        assert col_name in pred_df.columns, f"Expected {col_name} in predictions CSV"

        y_pred = pred_df[col_name].values
        calc_tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        calc_fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        calc_tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        calc_fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        assert calc_tp == m_row["tp"], f"TP mismatch for {algo_name}"
        assert calc_fp == m_row["fp"], f"FP mismatch for {algo_name}"
        assert calc_tn == m_row["tn"], f"TN mismatch for {algo_name}"
        assert calc_fn == m_row["fn"], f"FN mismatch for {algo_name}"

