#!/usr/bin/env python3
"""Runner Script for EstateIQ Model Training & Comparative Benchmark.

Trains candidate machine learning models (Random Forest, Isolation Forest, baselines)
on synthetic facility telemetry, calibrates decision thresholds, and evaluates against
EstateIQ-DIF across held-out test splits and cross-building generalization.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmarks.model_training_bench import ModelTrainingBenchmarkSuite


def main():
    parser = argparse.ArgumentParser(description="EstateIQ Model Training & Comparative Benchmark Runner")
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="facility_dataset/data/synthetic_model_training/energy_readings_model_training.csv",
        help="Path to synthetic energy readings dataset",
    )
    parser.add_argument(
        "--events-path",
        type=str,
        default="facility_dataset/data/synthetic_model_training/ground_truth_events_model_training.csv",
        help="Path to ground-truth events table",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/presentation/synthetic_model_training",
        help="Output directory for reports, metrics, models, and figures",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--false-alert-budget",
        type=float,
        default=1.0,
        help="Maximum allowable false alerts per building-day on validation data (default: 1.0)",
    )

    args = parser.parse_args()

    suite = ModelTrainingBenchmarkSuite(
        dataset_path=Path(args.dataset_path) if args.dataset_path else None,
        events_path=Path(args.events_path) if args.events_path else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        false_alert_budget_bld_day=args.false_alert_budget,
        random_seed=args.seed,
    )

    suite.run_benchmark()


if __name__ == "__main__":
    main()

