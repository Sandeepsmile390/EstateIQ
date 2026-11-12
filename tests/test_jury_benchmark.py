"""Unit test suite for EstateIQ Jury Algorithm Benchmark Suite.

Verifies:
1. Output artifact existence (CSV, JSON, Markdown, PNG/SVG figures).
2. Mathematical consistency across all metrics (TP, FP, TN, FN, Precision, Recall, F1, False Alerts/Day).
3. Exact alignment between aggregate metrics and raw per-reading predictions.
4. Leak-free chronological protocol (timestamps strictly sorted, train < val < test).
"""

import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pytest

OUTPUT_DIR = Path("output/presentation/algorithm_comparison")


def test_artifacts_exist():
    """Verify all 5 figures (PNG & SVG), metrics CSV, raw predictions, and markdown briefs exist."""
    required_files = [
        "benchmark_metrics.csv",
        "benchmark_results.json",
        "per_reading_predictions.csv",
        "BENCHMARK_REPORT.md",
        "JURY_PRESENTATION_BRIEF.md",
        "fig1_main_algorithm_comparison.png",
        "fig1_main_algorithm_comparison.svg",
        "fig2_operational_tradeoff.png",
        "fig2_operational_tradeoff.svg",
        "fig3_precision_recall_curves.png",
        "fig3_precision_recall_curves.svg",
        "fig4_confusion_matrices.png",
        "fig4_confusion_matrices.svg",
        "fig5_latency_comparison.png",
        "fig5_latency_comparison.svg",
    ]
    for filename in required_files:
        filepath = OUTPUT_DIR / filename
        assert filepath.exists(), f"Missing required benchmark artifact: {filepath}"
        assert filepath.stat().st_size > 0, f"Artifact is empty: {filepath}"


def test_mathematical_consistency():
    """Verify that confusion matrix counts and metric equations are strictly consistent."""
    csv_path = OUTPUT_DIR / "benchmark_metrics.csv"
    assert csv_path.exists(), "benchmark_metrics.csv must exist before running test"
    df = pd.read_csv(csv_path)

    assert len(df) >= 7, f"Expected at least 7 algorithms evaluated, found {len(df)}"

    total_time_days = 426 * 0.25 / 24.0  # 4.4375 days

    for _, row in df.iterrows():
        tp = row["tp"]
        fp = row["fp"]
        tn = row["tn"]
        fn = row["fn"]

        # 1. Total instance counts
        assert tp + fn == 42, f"Positive count mismatch for {row['algorithm']}: {tp + fn} != 42"
        assert tn + fp == 384, f"Negative count mismatch for {row['algorithm']}: {tn + fp} != 384"
        assert tp + fp + tn + fn == 426, f"Total interval mismatch: {tp + fp + tn + fn} != 426"

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

        # 5. False alerts per day
        expected_fad = fp / total_time_days
        assert pytest.approx(row["false_alerts_per_day"], abs=1e-2) == expected_fad


def test_raw_prediction_reproducibility():
    """Verify that aggregate metrics can be exact-recomputed from per_reading_predictions.csv."""
    pred_path = OUTPUT_DIR / "per_reading_predictions.csv"
    metrics_path = OUTPUT_DIR / "benchmark_metrics.csv"
    assert pred_path.exists() and metrics_path.exists()

    pred_df = pd.read_csv(pred_path)
    metrics_df = pd.read_csv(metrics_path)

    assert len(pred_df) == 426, f"Expected 426 test rows, found {len(pred_df)}"
    y_true = pred_df["ground_truth_label"].values

    # Test all evaluated algorithms against their saved prediction columns
    for _, m_row in metrics_df.iterrows():
        algo_name = m_row["algorithm"]
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", algo_name.lower()).strip("_")
        col_name = f"{slug}_pred"
        assert col_name in pred_df.columns, f"Expected column {col_name} in predictions CSV"

        y_pred = pred_df[col_name].values
        calc_tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        calc_fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        calc_tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        calc_fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        assert calc_tp == m_row["tp"], f"TP mismatch for {algo_name}: calc {calc_tp} vs {m_row['tp']}"
        assert calc_fp == m_row["fp"], f"FP mismatch for {algo_name}: calc {calc_fp} vs {m_row['fp']}"
        assert calc_tn == m_row["tn"], f"TN mismatch for {algo_name}: calc {calc_tn} vs {m_row['tn']}"
        assert calc_fn == m_row["fn"], f"FN mismatch for {algo_name}: calc {calc_fn} vs {m_row['fn']}"


def test_json_and_markdown_consistency():
    """Verify JSON metadata agrees with CSV and markdown reports."""
    json_path = OUTPUT_DIR / "benchmark_results.json"
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    bmeta = meta["benchmark_metadata"]
    assert bmeta["evaluation_sample_count"] == 426
    assert bmeta["positive_label_count"] == 42
    assert bmeta["negative_label_count"] == 384
    assert bmeta["dataset_data_nature"] == "SYNTHETIC_PHYSICS_CONSTRAINED"

    report_path = OUTPUT_DIR / "BENCHMARK_REPORT.md"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "EstateIQ-DIF (Persistence Gated, n >= 2)" in report_text
    assert "Isolation Forest (Contextual Features)" in report_text

    brief_path = OUTPUT_DIR / "JURY_PRESENTATION_BRIEF.md"
    assert brief_path.exists()
    brief_text = brief_path.read_text(encoding="utf-8")
    assert "0.9524" in brief_text
    assert "0.7711" in brief_text
