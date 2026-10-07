"""
EstateIQ-DIF Performance & Complexity Benchmark Script (tests/benchmark_dif.py).
Measures average latency, p95 latency, early-exit rate, models executed, and SHAP execution frequency.
"""

import time
import pandas as pd
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.types import EventData

def run_benchmark(num_samples: int = 100):
    dif_engine = EstateIQDIF()
    latencies = []

    print(f"Starting EstateIQ-DIF Benchmark ({num_samples} iterations)...")

    for i in range(num_samples):
        # Alternate between normal readings (80%) and anomalous readings (20%)
        is_anomaly = (i % 5 == 0)
        actual_kwh = 145.0 if is_anomaly else 65.0

        event = EventData(
            event_id=f"EVT_{i:04d}",
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block B Hostel",
            timestamp="2026-10-07T10:00:00",
            actual_kwh=actual_kwh,
            hour=14,
            day_of_week=2,
            occupancy=140 if is_anomaly else 60,
            temperature=32.0 if is_anomaly else 26.0,
            hvac_load=75.0 if is_anomaly else 25.0
        )

        t0 = time.time()
        res = dif_engine.analyze(event)
        t1 = time.time()

        latencies.append((t1 - t0) * 1000.0)

    avg_lat = sum(latencies) / len(latencies)
    latencies.sort()
    p95_lat = latencies[int(len(latencies) * 0.95)]

    summary = dif_engine.monitor.get_summary()

    print("\n==================================================")
    print("ESTATEIQ-DIF BENCHMARK RESULTS")
    print("==================================================")
    print(f"Total Telemetry Requests Evaluated: {num_samples}")
    print(f"Average Inference Latency:           {avg_lat:.2f} ms")
    print(f"p95 Latency:                         {p95_lat:.2f} ms")
    print(f"Early Exit Percentage (Fast Path):   {summary['early_exit_percentage']}%")
    print(f"Selective SHAP Frequency:           {summary['shap_execution_percentage']}%")
    print("==================================================")

if __name__ == "__main__":
    run_benchmark(100)
