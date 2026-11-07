"""Complexity model and reproducible single-event latency microbenchmark."""

from __future__ import annotations

import platform
import statistics
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.types import EventData


COMPLEXITY_TABLE: List[Dict[str, str]] = [
    {"stage": "Input validation and heuristic baseline", "time_complexity": "O(1)", "space_complexity": "O(1)",
     "assumptions": "Fixed number of scalar fields; no dataframe supplied."},
    {"stage": "Fitted seasonal baseline lookup", "time_complexity": "O(1)", "space_complexity": "O(1) per query",
     "assumptions": "Hash lookup by building and 15-minute weekday slot; fitted profile storage O(S)."},
    {"stage": "Rule checks and anomaly score fusion", "time_complexity": "O(1)", "space_complexity": "O(1)",
     "assumptions": "Fixed number of scalar rules and evidence signals; no IF/LOF estimator is invoked."},
    {"stage": "Temporal persistence state", "time_complexity": "O(1) expected", "space_complexity": "O(B)",
     "assumptions": "Dictionary lookup/update; B is bounded by the configured building-state capacity."},
    {"stage": "Impact, risk and priority arithmetic", "time_complexity": "O(1)", "space_complexity": "O(1)",
     "assumptions": "Closed-form calculation; annualized impact is a continuation scenario."},
    {"stage": "Optional dataframe quality scan", "time_complexity": "O(NF)", "space_complexity": "O(NF) worst case",
     "assumptions": "N telemetry rows and F columns; used only when a dataframe is passed to analyze."},
    {"stage": "Seasonal baseline fit", "time_complexity": "O(N) expected", "space_complexity": "O(N+S)",
     "assumptions": "One-time grouped robust statistics on N training rows, yielding S building/time-slot profiles."},
    {"stage": "Core event path", "time_complexity": "O(1) expected", "space_complexity": "O(1) incremental; O(S+B) retained",
     "assumptions": "Fixed model/profile and no optional telemetry dataframe; average-case dictionary operations."},
]


class EmpiricalComplexityBenchmark:
    """Measure warmed, deterministic per-event latency without RSS-delta claims."""

    @staticmethod
    def run_benchmark(sample_counts: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        counts = sample_counts or [100, 1000]
        if any(count < 1 for count in counts):
            raise ValueError("sample counts must be positive")
        rows = []
        for count in counts:
            engine = EstateIQDIF()
            def process(index: int) -> None:
                stamp = datetime(2026, 11, 1, tzinfo=timezone(timedelta(hours=5, minutes=30))) + timedelta(minutes=15 * index)
                event = EventData(
                    event_id=f"BENCH-{index}", facility_id="BENCH-FACILITY",
                    building_id="BENCH-BUILDING",
                    timestamp=stamp.isoformat(),
                    actual_kwh=55.0 + (index % 7) * 0.1, hour=stamp.hour,
                    day_of_week=stamp.weekday(), occupancy=100,
                    temperature=25.0, hvac_load=20.0, interval_hours=0.25,
                )
                engine.analyze(event)

            for warm_idx in range(20):
                process(warm_idx)
            latencies = []
            overall = time.perf_counter()
            for idx in range(count):
                begin = time.perf_counter()
                process(idx + 20)
                latencies.append((time.perf_counter() - begin) * 1000.0)
            elapsed = time.perf_counter() - overall
            ordered = sorted(latencies)
            p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
            p99 = ordered[min(len(ordered) - 1, int(0.99 * len(ordered)))]
            rows.append({
                "sample_count": count,
                "warmup_count": 20,
                "median_latency_ms": round(statistics.median(latencies), 4),
                "p95_latency_ms": round(p95, 4),
                "p99_latency_ms": round(p99, 4),
                "throughput_events_per_sec": round(count / max(elapsed, 1e-12), 2),
                "environment": f"Python {platform.python_version()} / {platform.system()} / {platform.machine()}",
                "measurement_note": "No dataframe; heuristic cold-start baseline; memory delta not reported.",
            })
        return rows
