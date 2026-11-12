#!/usr/bin/env python3
"""Root Runner for EstateIQ-DIF V3 Scientific Algorithm Benchmark.

Executes the end-to-end evaluation comparing EstateIQ-DIF with competitive
baselines (Isolation Forest contextual/univariate, LOF, Seasonal Gaussian, Rolling Z-score, Static P99).
Includes adaptive baseline replay, domain rules verification, sensor-health monitoring,
validation-calibrated thresholding, multi-seed evaluation, and publication figure generation.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmarks.v3_benchmark import V3BenchmarkSuite
from src.data_generator_v2.generator_v2 import DatasetGeneratorV2


def main():
    parser = argparse.ArgumentParser(description="EstateIQ-DIF V3 Scientific Algorithm Benchmark Runner")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate synthetic V3 dataset and ground-truth events before benchmarking",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Primary random seed (default: 42)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[42, 123, 999],
        help="List of seeds for multi-seed stability evaluation (default: 42 123 999)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/presentation/algorithm_comparison_v3",
        help="Target output directory for V3 benchmark artifacts and figures",
    )
    parser.add_argument(
        "--dif-fixed-threshold",
        type=float,
        default=55.0,
        help="Fixed threshold for legacy comparator DIF (default: 55.0)",
    )
    parser.add_argument(
        "--false-alert-budget",
        type=float,
        default=1.0,
        help="Target maximum false alerts per building-day on nominal validation (default: 1.0)",
    )

    args = parser.parse_args()

    out_path = ROOT / args.output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    data_path = ROOT / "facility_dataset/data/synthetic_v2/energy_readings_v2.csv"
    events_path = ROOT / "facility_dataset/data/synthetic_v2/ground_truth_events_v2.csv"

    if args.regenerate or not data_path.exists() or not events_path.exists():
        print(f"[Runner] Generating synthetic dataset (Seed {args.seed})...")
        gen = DatasetGeneratorV2(seed=args.seed)
        df = gen.generate_raw_baseline_readings()
        events_df = gen.generate_events_table(df)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(data_path, index=False)
        events_df.to_csv(events_path, index=False)
        print(f"[Runner] Dataset saved to: {data_path}")

    # Run V3 Benchmark Suite
    suite = V3BenchmarkSuite(
        dataset_path=data_path,
        events_path=events_path,
        output_dir=out_path,
        seeds=args.seeds,
        dif_fixed_threshold=args.dif_fixed_threshold,
        false_alert_budget=args.false_alert_budget,
    )
    suite.run_full_benchmark()


if __name__ == "__main__":
    main()

