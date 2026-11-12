"""Configurable Multi-Mode Fault Injection Engine for Generator V2.

Implements realistic building operational faults and sensor-quality faults:
1. After-hours energy surge / base load creep
2. HVAC equipment stuck on / schedule mismatch
3. Gradual energy drift (refrigerant leak / degradation)
4. Short transient surge (1-2 interval micro-spikes)
5. Meter flatline (frozen sensor values)
6. Meter communication dropout (zero-readings during occupancy)
7. Weekend schedule mismatch

Tracks all ground-truth events with start/end timestamps, severity, and injection parameters.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class GroundTruthEvent:
    """Detailed record of an injected anomaly episode."""
    event_id: str
    building_id: str
    anomaly_type: str
    fault_category: str  # "building_fault" vs "sensor_quality_fault"
    start_timestamp: str
    end_timestamp: str
    duration_hours: float
    interval_count: int
    severity: str        # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    affected_fields: List[str]
    injection_parameters: Dict[str, Any]


@dataclass
class FaultScenario:
    """Specification for injecting a fault episode into telemetry."""
    event_id: str
    building_id: str
    anomaly_type: str
    fault_category: str
    start_time: str
    duration_hours: float
    severity: str
    parameters: Dict[str, Any]


def apply_fault_scenario(
    df: pd.DataFrame,
    scenario: FaultScenario,
    rng: np.random.Generator,
) -> Tuple[pd.DataFrame, GroundTruthEvent]:
    """Applies a single fault scenario to the DataFrame and returns the updated df and event record."""
    t_start = pd.to_datetime(scenario.start_time).tz_localize("Asia/Kolkata")
    t_end = t_start + pd.Timedelta(hours=scenario.duration_hours)

    bld_mask = df["building_id"] == scenario.building_id
    time_mask = (df["timestamp"] >= t_start) & (df["timestamp"] <= t_end)
    mask = bld_mask & time_mask

    affected_indices = df[mask].index
    interval_count = len(affected_indices)
    affected_fields = ["electricity_kwh"]

    if interval_count == 0:
        raise ValueError(
            f"Scenario {scenario.event_id} on {scenario.building_id} between {t_start} and {t_end} matched 0 rows!"
        )

    # 1. After-hours surge / base load creep
    if scenario.anomaly_type == "after_hours_surge":
        multiplier = scenario.parameters.get("multiplier", 2.5)
        df.loc[mask, "electricity_kwh"] = np.round(df.loc[mask, "electricity_kwh"] * multiplier, 3)
        if "hvac_kwh" in df.columns:
            df.loc[mask, "hvac_kwh"] = np.round(df.loc[mask, "hvac_kwh"] * multiplier, 3)
            affected_fields.append("hvac_kwh")

    # 2. HVAC equipment stuck on
    elif scenario.anomaly_type == "hvac_stuck_on":
        hvac_add_kw = scenario.parameters.get("extra_hvac_kw", 35.0)
        hvac_add_kwh = hvac_add_kw * 0.25  # 15-min interval
        df.loc[mask, "electricity_kwh"] = np.round(df.loc[mask, "electricity_kwh"] + hvac_add_kwh, 3)
        if "hvac_kwh" in df.columns:
            df.loc[mask, "hvac_kwh"] = np.round(df.loc[mask, "hvac_kwh"] + hvac_add_kwh, 3)
            affected_fields.append("hvac_kwh")
        if "power_factor" in df.columns:
            # Low inductive power factor during unneeded motor idling
            df.loc[mask, "power_factor"] = np.round(
                np.clip(df.loc[mask, "power_factor"] - 0.08, 0.75, 0.99), 3
            )
            affected_fields.append("power_factor")

    # 3. Gradual energy drift (progressive degradation)
    elif scenario.anomaly_type == "gradual_drift":
        max_multiplier = scenario.parameters.get("max_drift_pct", 0.60)  # up to +60%
        # Linear progression from 0 to max_multiplier
        ramp = np.linspace(0.0, max_multiplier, interval_count)
        df.loc[mask, "electricity_kwh"] = np.round(
            df.loc[mask, "electricity_kwh"] * (1.0 + ramp), 3
        )
        if "hvac_kwh" in df.columns:
            df.loc[mask, "hvac_kwh"] = np.round(
                df.loc[mask, "hvac_kwh"] * (1.0 + ramp), 3
            )
            affected_fields.append("hvac_kwh")

    # 4. Short transient surge (micro-spike lasting 1-2 intervals)
    elif scenario.anomaly_type == "transient_surge":
        spike_multiplier = scenario.parameters.get("spike_multiplier", 3.0)
        df.loc[mask, "electricity_kwh"] = np.round(
            df.loc[mask, "electricity_kwh"] * spike_multiplier, 3
        )

    # 5. Meter flatline (frozen sensor)
    elif scenario.anomaly_type == "meter_flatline":
        flat_val = scenario.parameters.get("flat_kwh", 4.500)
        df.loc[mask, "electricity_kwh"] = flat_val
        if "power_factor" in df.columns:
            df.loc[mask, "power_factor"] = 0.920
            affected_fields.append("power_factor")

    # 6. Meter communication dropout (sensor drop to zero during day)
    elif scenario.anomaly_type == "meter_dropout":
        drop_val = scenario.parameters.get("drop_kwh", 0.0)
        df.loc[mask, "electricity_kwh"] = drop_val
        if "power_factor" in df.columns:
            df.loc[mask, "power_factor"] = 0.0
            affected_fields.append("power_factor")

    # 7. Weekend schedule mismatch
    elif scenario.anomaly_type == "weekend_schedule_mismatch":
        base_add_kwh = scenario.parameters.get("excess_kwh", 25.0)
        df.loc[mask, "electricity_kwh"] = np.round(
            df.loc[mask, "electricity_kwh"] + base_add_kwh, 3
        )
        if "lighting_kwh" in df.columns:
            df.loc[mask, "lighting_kwh"] = np.round(
                df.loc[mask, "lighting_kwh"] + (base_add_kwh * 0.4), 3
            )
            affected_fields.append("lighting_kwh")

    else:
        raise ValueError(f"Unknown anomaly type: {scenario.anomaly_type}")

    # Mark pointwise labels
    df.loc[mask, "anomaly_flag"] = 1
    df.loc[mask, "anomaly_type"] = scenario.anomaly_type
    df.loc[mask, "fault_category"] = scenario.fault_category
    df.loc[mask, "event_id"] = scenario.event_id

    event_record = GroundTruthEvent(
        event_id=scenario.event_id,
        building_id=scenario.building_id,
        anomaly_type=scenario.anomaly_type,
        fault_category=scenario.fault_category,
        start_timestamp=t_start.isoformat(),
        end_timestamp=t_end.isoformat(),
        duration_hours=float(scenario.duration_hours),
        interval_count=int(interval_count),
        severity=scenario.severity,
        affected_fields=affected_fields,
        injection_parameters=scenario.parameters,
    )

    return df, event_record


def get_canonical_v2_scenarios() -> List[FaultScenario]:
    """Returns the comprehensive suite of 8 diverse fault scenarios for Generator V2.
    
    All events are scheduled strictly within the held-out test window (>= 2026-04-01).
    Ensures 100% nominal, unpolluted data in the training (Jan-Mar 15) and validation (Mar 16-31) periods.
    """
    return [
        # Scenario 1: After-Hours Energy Surge in Academic Block A
        FaultScenario(
            event_id="EVT_V2_001",
            building_id="BLD001",
            anomaly_type="after_hours_surge",
            fault_category="building_fault",
            start_time="2026-04-10 22:00:00",
            duration_hours=6.0,  # 24 intervals
            severity="HIGH",
            parameters={"multiplier": 2.65, "reason": "Computer lab lighting and workstations left running overnight"},
        ),
        # Scenario 2: HVAC Equipment Stuck On in Computer Science Block
        FaultScenario(
            event_id="EVT_V2_002",
            building_id="BLD003",
            anomaly_type="hvac_stuck_on",
            fault_category="building_fault",
            start_time="2026-04-22 01:00:00",
            duration_hours=14.0,  # 56 intervals
            severity="CRITICAL",
            parameters={"extra_hvac_kw": 40.0, "reason": "Chiller contactor welded shut, running full cooling overnight"},
        ),
        # Scenario 3: Gradual Energy Drift (Refrigerant leak) in Administration Block
        FaultScenario(
            event_id="EVT_V2_003",
            building_id="BLD004",
            anomaly_type="gradual_drift",
            fault_category="building_fault",
            start_time="2026-05-05 08:00:00",
            duration_hours=72.0,  # 288 intervals (3 days of progressive drift)
            severity="MEDIUM",
            parameters={"max_drift_pct": 0.55, "reason": "Slow refrigerant loss causing compressor COP degradation"},
        ),
        # Scenario 4: Short Transient Surge in Library (2 intervals) - Tests persistence gate vs pointwise
        FaultScenario(
            event_id="EVT_V2_004",
            building_id="BLD005",
            anomaly_type="transient_surge",
            fault_category="building_fault",
            start_time="2026-05-18 10:15:00",
            duration_hours=0.5,  # Exactly 2 intervals (10:15 and 10:30)
            severity="LOW",
            parameters={"spike_multiplier": 2.80, "reason": "Heavy elevator motor testing spike"},
        ),
        # Scenario 5: Isolated Single-Interval Surge in Library (1 interval) - Gated detector should debounce this
        FaultScenario(
            event_id="EVT_V2_005",
            building_id="BLD005",
            anomaly_type="transient_surge",
            fault_category="building_fault",
            start_time="2026-05-18 14:00:00",
            duration_hours=0.25,  # Exactly 1 interval
            severity="LOW",
            parameters={"spike_multiplier": 3.20, "reason": "Single micro-spike transient"},
        ),
        # Scenario 6: Meter Flatline (Sensor ADC frozen) in Academic Block B
        FaultScenario(
            event_id="EVT_V2_006",
            building_id="BLD002",
            anomaly_type="meter_flatline",
            fault_category="sensor_quality_fault",
            start_time="2026-06-02 02:00:00",
            duration_hours=8.0,  # 32 intervals
            severity="MEDIUM",
            parameters={"flat_kwh": 6.800, "reason": "Submeter Modbus register frozen at fixed telemetry value"},
        ),
        # Scenario 7: Meter Communication Dropout (Telemetry drops to zero) in Academic Block A
        FaultScenario(
            event_id="EVT_V2_007",
            building_id="BLD001",
            anomaly_type="meter_dropout",
            fault_category="sensor_quality_fault",
            start_time="2026-06-15 11:00:00",
            duration_hours=3.0,  # 12 intervals during active campus daytime
            severity="HIGH",
            parameters={"drop_kwh": 0.0, "reason": "Gateway LoRaWAN packet loss causing zero readings"},
        ),
        # Scenario 8: Weekend Schedule Mismatch in Computer Science Block
        FaultScenario(
            event_id="EVT_V2_008",
            building_id="BLD003",
            anomaly_type="weekend_schedule_mismatch",
            fault_category="building_fault",
            start_time="2026-06-27 09:00:00",
            duration_hours=30.0,  # 120 intervals across Saturday and Sunday
            severity="HIGH",
            parameters={"excess_kwh": 32.0, "reason": "HVAC AHU running full schedule on unbooked holiday weekend"},
        ),
    ]


def get_model_training_scenarios() -> List[FaultScenario]:
    """Returns an extended suite of fault scenarios across Train, Val, and Test.
    
    Includes:
    - 5 Training episodes (Jan-Feb 2026) enabling supervised model (Random Forest) training.
    - 2 Validation episodes (Mid-to-Late Mar 2026) for supervised threshold calibration.
    - The exact 8 canonical held-out test episodes (Apr-Jun 2026) for unpolluted evaluation.
    """
    scenarios = [
        # --- TRAINING PERIOD EPISODES (Jan 1 – Mar 15) ---
        FaultScenario(
            event_id="TRN_EVT_001",
            building_id="BLD002",
            anomaly_type="after_hours_surge",
            fault_category="building_fault",
            start_time="2026-01-15 22:00:00",
            duration_hours=6.0,
            severity="HIGH",
            parameters={"multiplier": 2.50, "reason": "Training: Evening laboratory lighting left active overnight"},
        ),
        FaultScenario(
            event_id="TRN_EVT_002",
            building_id="BLD001",
            anomaly_type="hvac_stuck_on",
            fault_category="building_fault",
            start_time="2026-01-28 01:00:00",
            duration_hours=14.0,
            severity="CRITICAL",
            parameters={"extra_hvac_kw": 35.0, "reason": "Training: VRF heat exchanger stuck at full cooling overnight"},
        ),
        FaultScenario(
            event_id="TRN_EVT_003",
            building_id="BLD004",
            anomaly_type="weekend_schedule_mismatch",
            fault_category="building_fault",
            start_time="2026-02-07 09:00:00",
            duration_hours=28.0,
            severity="HIGH",
            parameters={"excess_kwh": 26.0, "reason": "Training: Admin block HVAC running full schedule over Saturday/Sunday"},
        ),
        FaultScenario(
            event_id="TRN_EVT_004",
            building_id="BLD003",
            anomaly_type="meter_flatline",
            fault_category="sensor_quality_fault",
            start_time="2026-02-18 02:00:00",
            duration_hours=8.0,
            severity="MEDIUM",
            parameters={"flat_kwh": 7.200, "reason": "Training: Submeter Modbus register frozen at fixed telemetry value"},
        ),
        FaultScenario(
            event_id="TRN_EVT_005",
            building_id="BLD005",
            anomaly_type="meter_dropout",
            fault_category="sensor_quality_fault",
            start_time="2026-02-25 11:00:00",
            duration_hours=3.0,
            severity="HIGH",
            parameters={"drop_kwh": 0.0, "reason": "Training: Gateway LoRaWAN packet loss causing zero readings"},
        ),

        # --- VALIDATION PERIOD EPISODES (Mar 16 – Mar 31) ---
        FaultScenario(
            event_id="VAL_EVT_001",
            building_id="BLD003",
            anomaly_type="after_hours_surge",
            fault_category="building_fault",
            start_time="2026-03-18 22:00:00",
            duration_hours=5.0,
            severity="HIGH",
            parameters={"multiplier": 2.40, "reason": "Validation: Server room auxiliary cooling surge"},
        ),
        FaultScenario(
            event_id="VAL_EVT_002",
            building_id="BLD002",
            anomaly_type="hvac_stuck_on",
            fault_category="building_fault",
            start_time="2026-03-25 01:00:00",
            duration_hours=12.0,
            severity="CRITICAL",
            parameters={"extra_hvac_kw": 32.0, "reason": "Validation: Contactor stuck on during unseasonable warm night"},
        ),
    ]

    # Append the exact 8 canonical test scenarios
    scenarios.extend(get_canonical_v2_scenarios())
    return scenarios


def inject_fault_scenarios(
    df: pd.DataFrame,
    scenarios: Optional[List[FaultScenario]] = None,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Injects all configured fault scenarios into telemetry and returns (df_labeled, df_events)."""
    rng = np.random.default_rng(seed)

    if scenarios is None:
        scenarios = get_canonical_v2_scenarios()

    df_out = df.copy()
    if "anomaly_flag" not in df_out.columns:
        df_out["anomaly_flag"] = 0
    if "anomaly_type" not in df_out.columns:
        df_out["anomaly_type"] = "normal"
    if "fault_category" not in df_out.columns:
        df_out["fault_category"] = "nominal"
    if "event_id" not in df_out.columns:
        df_out["event_id"] = "none"

    event_records: List[GroundTruthEvent] = []

    for sc in scenarios:
        df_out, ev = apply_fault_scenario(df_out, sc, rng)
        event_records.append(ev)

    events_df = pd.DataFrame([asdict(e) for e in event_records])
    return df_out, events_df

