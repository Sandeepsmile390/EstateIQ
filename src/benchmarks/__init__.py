"""EstateIQ Algorithm Benchmark Suite.

Provides reproducible, leakage-free benchmarking of EstateIQ-DIF against
reference baselines for energy forecasting, anomaly detection, and computational complexity.
"""

from src.benchmarks.dataset_loader import DatasetLoader, DatasetMetadata
from src.benchmarks.metrics_utils import (
    calculate_forecasting_metrics,
    calculate_classification_metrics,
    calculate_event_level_metrics,
)
from src.benchmarks.forecasting_bench import EnergyForecastingBenchmark
from src.benchmarks.anomaly_bench import AnomalyDetectionBenchmark
from src.benchmarks.complexity_bench import ComplexityBenchmark

__all__ = [
    "DatasetLoader",
    "DatasetMetadata",
    "calculate_forecasting_metrics",
    "calculate_classification_metrics",
    "calculate_event_level_metrics",
    "EnergyForecastingBenchmark",
    "AnomalyDetectionBenchmark",
    "ComplexityBenchmark",
]

