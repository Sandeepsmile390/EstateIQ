"""
EstateIQ Energy What-If Scenario Simulation Engine (src/analytics/scenarios.py).
Implements the exact what-if calculation specified in Section 6.3 of the Implementation Report:
- Estimated energy reduction (kWh) = forecast baseline (kWh) * assumed reduction fraction
- Estimated cost reduction (INR) = estimated energy reduction * configurable tariff (₹/kWh)
- Outputs: baseline, scenario, delta, units, tariff assumptions, time window, and explicit disclaimer:
  "Estimate, not verified savings."
- Persists scenario runs into scenarios database table.
"""

import json
import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.data.canonical_db import get_facility, record_scenario

def simulate_energy_scenario(
    facility_id: str = "COLLEGE_01",
    zone_id: Optional[str] = None,
    reduction_pct: float = 10.0,
    tariff_inr_per_kwh: Optional[float] = None,
    time_window_hours: int = 24,
    baseline_kwh: Optional[float] = None,
    hvac_setback_deg: float = 2.0,
    solar_addition_kwp: float = 0.0,
    user_id: str = "operator",
    persist: bool = True,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Computes transparent energy what-if simulation comparing baseline vs scenario.
    Labels results strictly as analytical estimates, not measured/verified outcomes.
    """
    fac = get_facility(facility_id, db_path=db_path) or {}
    fac_cfg = fac.get("config", {})

    tariff = tariff_inr_per_kwh or fac_cfg.get("energy_tariff_inr_per_kwh", 9.50)

    # If baseline is not supplied, compute 24h baseline load from 50 kWh/hr default or forecast
    if baseline_kwh is None or baseline_kwh <= 0:
        base_load = 1000.0 if time_window_hours == 24 else float(time_window_hours * 45.0)
    else:
        base_load = float(baseline_kwh)

    # Reduction fraction
    fraction = max(0.0, min(1.0, reduction_pct / 100.0))

    # Proportional calculation
    estimated_energy_reduction_kwh = round(base_load * fraction, 2)
    scenario_kwh = round(base_load - estimated_energy_reduction_kwh, 2)
    estimated_cost_reduction_inr = round(estimated_energy_reduction_kwh * tariff, 2)

    # Solar generation offset (optional additional credit)
    solar_gen_kwh = round(solar_addition_kwp * 4.2 * (time_window_hours / 24.0), 2) if solar_addition_kwp > 0 else 0.0
    net_grid_scenario_kwh = max(0.0, round(scenario_kwh - solar_gen_kwh, 2))

    assumptions = [
        f"Configured grid electricity tariff: ₹{tariff:.2f}/kWh (commercial campus rate)",
        f"Assumed uniform load reduction: {reduction_pct:.1f}% applied across {time_window_hours}-hour horizon",
        f"HVAC thermostat setback: +{hvac_setback_deg:.1f}°C during active cooling periods",
        "Simplified proportional scenario calculation (does not guarantee identical physical savings in real building)",
        "Estimate, not verified savings. Field measurement and verification (M&V) required post-intervention."
    ]
    if solar_addition_kwp > 0:
        assumptions.append(f"Solar PV generation modeled at 4.2 peak sun hours/day for {solar_addition_kwp} kWp capacity")

    inputs_payload = {
        "facility_id": facility_id,
        "zone_id": zone_id or "All Zones",
        "reduction_pct": reduction_pct,
        "tariff_inr_per_kwh": tariff,
        "time_window_hours": time_window_hours,
        "hvac_setback_deg": hvac_setback_deg,
        "solar_addition_kwp": solar_addition_kwp
    }

    baseline_payload = {
        "baseline_kwh": base_load,
        "baseline_cost_inr": round(base_load * tariff, 2),
        "units": {"energy": "kWh", "cost": "INR (₹)"}
    }

    scenario_payload = {
        "scenario_kwh": scenario_kwh,
        "scenario_cost_inr": round(scenario_kwh * tariff, 2),
        "net_grid_kwh": net_grid_scenario_kwh,
        "solar_generation_kwh": solar_gen_kwh,
        "delta_reduction_kwh": estimated_energy_reduction_kwh,
        "delta_reduction_pct": reduction_pct,
        "delta_cost_savings_inr": estimated_cost_reduction_inr,
        "disclaimer": "Estimate, not verified savings. Simplified scenario calculation does not prove identical savings will occur in physical facility."
    }

    result = {
        "facility_id": facility_id,
        "zone_id": zone_id or "All Zones",
        "time_window_hours": time_window_hours,
        "baseline": baseline_payload,
        "scenario": scenario_payload,
        "delta": {
            "energy_reduction_kwh": estimated_energy_reduction_kwh,
            "cost_reduction_inr": estimated_cost_reduction_inr,
            "carbon_reduction_kg_co2": round(estimated_energy_reduction_kwh * 0.82, 1)  # Indian grid factor ~0.82 kg CO2/kWh
        },
        "tariff_assumptions": {
            "rate_inr_per_kwh": tariff,
            "source": "Configured facility rate"
        },
        "assumptions": assumptions,
        "disclaimer": "Estimate, not verified savings"
    }

    if persist:
        record_scenario(
            user_id=user_id,
            facility_id=facility_id,
            inputs=inputs_payload,
            baseline=baseline_payload,
            scenario=scenario_payload,
            assumptions=assumptions,
            db_path=db_path
        )

    return result
