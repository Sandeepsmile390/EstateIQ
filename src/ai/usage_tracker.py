"""
AI Usage & Latency Tracker (src/ai/usage_tracker.py).
Tracks request latency, status, model used, and fallback executions without logging secrets.
"""

import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AIUsageTracker:
    """Logs AI request metadata and health statistics."""

    def __init__(self):
        self.stats = {
            "total_ai_requests": 0,
            "successful_groq_calls": 0,
            "fallback_calls": 0,
            "last_success_time": None,
            "last_failure_time": None,
            "last_error": None,
            "total_latency_ms": 0.0
        }

    def log_request(self, model: str, duration_ms: float, success: bool, fallback_used: bool, error_msg: str = ""):
        self.stats["total_ai_requests"] += 1
        self.stats["total_latency_ms"] += duration_ms

        if success and not fallback_used:
            self.stats["successful_groq_calls"] += 1
            self.stats["last_success_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            self.stats["fallback_calls"] += 1
            self.stats["last_failure_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if error_msg:
                self.stats["last_error"] = error_msg

        logger.info(
            "AI Request Profile | Model: %s | Latency: %.2fms | Success: %s | Fallback: %s",
            model, duration_ms, success, fallback_used
        )

    def get_health(self) -> Dict[str, Any]:
        total = max(1, self.stats["total_ai_requests"])
        avg_latency = round(self.stats["total_latency_ms"] / total, 2)

        return {
            "total_requests": self.stats["total_ai_requests"],
            "successful_groq_calls": self.stats["successful_groq_calls"],
            "fallback_calls": self.stats["fallback_calls"],
            "avg_latency_ms": avg_latency,
            "last_success": self.stats["last_success_time"],
            "last_failure": self.stats["last_failure_time"],
            "last_error": self.stats["last_error"],
            "provenance": "AI_USAGE_TRACKER"
        }

GLOBAL_USAGE_TRACKER = AIUsageTracker()
