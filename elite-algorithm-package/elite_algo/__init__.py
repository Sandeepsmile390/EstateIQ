"""Public API for EstateIQ-DIF.

The package exposes the implemented electricity anomaly-triage engine and its
seasonal baseline. Forecasting/evaluation helpers are optional modules; this
core API does not claim to run a trained ML ensemble.
"""

from src.intelligence.config import DIFConfig
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.seasonal_baseline import BaselineEstimate, SeasonalBaselineModel
from src.intelligence.types import DecisionResult, EventData

__version__ = "1.1.0"
__author__ = "Team Elite"

__all__ = [
    "BaselineEstimate",
    "DecisionResult",
    "DIFConfig",
    "EstateIQDIF",
    "EventData",
    "SeasonalBaselineModel",
]
