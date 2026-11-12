#!/usr/bin/env python3
"""
EstateIQ-DIF Algorithm Benchmark Runner.

Executes a fair, reproducible benchmark comparing EstateIQ-DIF against
Isolation Forest, Local Outlier Factor, Seasonal Gaussian, and baseline
algorithms on canonical facility energy telemetry.

Usage:
    python run_algorithm_benchmark.py
"""

import sys
from pathlib import Path

# Add root directory to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.benchmarks.jury_benchmark import JuryBenchmarkSuite


def main():
    print("=" * 80)
    print("Launching EstateIQ-DIF Official Algorithm Benchmark Suite...")
    print("=" * 80)
    suite = JuryBenchmarkSuite()
    suite.run()
    print("\nBenchmark completed successfully. Evidence package saved to:")
    print("output/presentation/algorithm_comparison/")


if __name__ == "__main__":
    main()

