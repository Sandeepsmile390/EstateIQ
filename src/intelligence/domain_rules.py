"""Deterministic operating-rule evidence used by the Elite DIF pipeline."""

import math
from typing import Any, Dict, Optional

from src.intelligence.types import EventData


def evaluate_domain_rules(event: EventData, expected_kwh: Optional[float] = None,
                          after_hours_surge_ratio: float = 1.8) -> Dict[str, Any]:
    """Return auditable rule outcomes; absent optional sensors are not imputed."""
    features = event.extra_features or {}
    power_factor = features.get("power_factor")
    try:
        power_factor = float(power_factor) if power_factor is not None else None
        if power_factor is not None and not math.isfinite(power_factor):
            power_factor = None
    except (TypeError, ValueError):
        power_factor = None
    reference = max(float(expected_kwh or 0.0), 1e-9)
    violations = {
        "off_peak_surge": (event.hour >= 20 or event.hour <= 5)
        and expected_kwh is not None and event.actual_kwh >= reference * after_hours_surge_ratio,
        "hvac_temperature_mismatch": (
            (event.temperature > 30.0 and event.hvac_load < 10.0)
            or (event.temperature < 20.0 and event.hvac_load > 80.0)
        ),
        "low_power_factor": power_factor is not None and 0.0 < power_factor < 0.82,
    }
    active = [name for name, triggered in violations.items() if triggered]
    return {"violations": violations, "active_rules": active, "has_violation": bool(active)}
