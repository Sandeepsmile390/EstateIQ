"""
Complexity & Performance Monitor (src/intelligence/complexity_monitor.py).
Profiles theoretical and runtime latency across Path A (Fast), Path B (Intelligence), and Path C (Critical).
"""

import time
from typing import Dict, Any, List

class ComplexityMonitor:
    """Profiles execution latency, models executed, and early exit rates."""

    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "early_exits": 0,
            "fast_path_count": 0,
            "intelligence_path_count": 0,
            "critical_path_count": 0,
            "shap_executions": 0
        }

    def record_execution(
        self,
        path: str,
        early_exit: bool,
        shap_executed: bool,
        duration_ms: float
    ):
        self.stats["total_requests"] += 1
        if early_exit:
            self.stats["early_exits"] += 1
        if path == "PATH_A_FAST":
            self.stats["fast_path_count"] += 1
        elif path == "PATH_B_INTELLIGENCE":
            self.stats["intelligence_path_count"] += 1
        else:
            self.stats["critical_path_count"] += 1
        if shap_executed:
            self.stats["shap_executions"] += 1

    def get_summary(self) -> Dict[str, Any]:
        total = max(1, self.stats["total_requests"])
        early_exit_pct = round((self.stats["early_exits"] / total) * 100.0, 1)
        shap_pct = round((self.stats["shap_executions"] / total) * 100.0, 1)

        return {
            "stats": self.stats,
            "early_exit_percentage": early_exit_pct,
            "shap_execution_percentage": shap_pct,
            "theoretical_complexity": {
                "fast_path": "O(1) Contextual residual check",
                "intelligence_path": "O(N_models) Adaptive ensemble evaluation",
                "critical_path": "O(N_models + SHAP) Full analysis & optimization"
            }
        }
