"""
Canonical Telemetry Schema and Normalization Engine (src/data/telemetry_schema.py).
Defines authoritative schemas, canonical metric names, unit definitions, validation rules,
and bidirectional compatibility adapters for real sensors, IoT simulator, and edge MQTT gateways.
"""

import math
import uuid
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    REAL_SENSOR = "real_sensor"
    SIMULATED_IOT = "simulated_iot"
    SYNTHETIC = "synthetic"
    DERIVED = "derived"
    PREDICTED = "predicted"


class MetricQuality(str, Enum):
    GOOD = "good"
    DEGRADED = "degraded"
    BAD = "bad"
    STALE = "stale"


class DeviceHealthStatus(str, Enum):
    ONLINE = "ONLINE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


# --- CANONICAL METRIC NAMES AND UNITS ---
# Map legacy and variant metric names to canonical name and expected unit
CANONICAL_METRIC_MAP: Dict[str, Tuple[str, str]] = {
    # Electricity
    "cumulative_energy_kwh": ("cumulative_energy_kwh", "kWh"),
    "energy_import_kwh": ("cumulative_energy_kwh", "kWh"),
    # Interval energy (for example, per 15-minute reporting window) is not a totalizer.
    "energy_kwh": ("energy_kwh", "kWh"),
    "electricity_kwh": ("energy_kwh", "kWh"),
    "cumulative_kwh": ("cumulative_energy_kwh", "kWh"),

    "active_power_kw": ("active_power_kw", "kW"),
    "power_kw": ("active_power_kw", "kW"),
    "active_power": ("active_power_kw", "kW"),
    "power": ("active_power_kw", "kW"),

    "voltage_v": ("voltage_v", "V"),
    "voltage": ("voltage_v", "V"),
    "voltage_l1_v": ("voltage_l1_v", "V"),
    "voltage_l2_v": ("voltage_l2_v", "V"),
    "voltage_l3_v": ("voltage_l3_v", "V"),

    "current_a": ("current_a", "A"),
    "current": ("current_a", "A"),
    "current_l1_a": ("current_l1_a", "A"),
    "current_l2_a": ("current_l2_a", "A"),
    "current_l3_a": ("current_l3_a", "A"),

    "power_factor": ("power_factor", "ratio"),
    "power_factor_total": ("power_factor", "ratio"),
    "pf": ("power_factor", "ratio"),

    "frequency_hz": ("frequency_hz", "Hz"),
    "frequency": ("frequency_hz", "Hz"),

    "maximum_demand_kw": ("maximum_demand_kw", "kW"),
    "max_demand_kw": ("maximum_demand_kw", "kW"),
    "maximum_demand_kva": ("maximum_demand_kva", "kVA"),
    "max_demand_kva": ("maximum_demand_kva", "kVA"),

    "thd_voltage_pct": ("thd_voltage_pct", "%"),
    "thd_current_pct": ("thd_current_pct", "%"),
    "unbalance_voltage_pct": ("unbalance_voltage_pct", "%"),
    "unbalance_current_pct": ("unbalance_current_pct", "%"),

    # Water
    "water_flow_lmin": ("water_flow_lmin", "L/min"),
    "water_flow_lpm": ("water_flow_lmin", "L/min"),
    "water_flow_rate_lpm": ("water_flow_lmin", "L/min"),
    "flow_rate_lmin": ("water_flow_lmin", "L/min"),
    "flow_lpm": ("water_flow_lmin", "L/min"),

    "cumulative_water_m3": ("cumulative_water_m3", "m3"),
    "water_total_m3": ("cumulative_water_m3", "m3"),
    "cumulative_m3": ("cumulative_water_m3", "m3"),

    "water_pressure_bar": ("water_pressure_bar", "bar"),
    "pressure_bar": ("water_pressure_bar", "bar"),
    "water_pressure_kpa": ("water_pressure_kpa", "kPa"),

    "tank_level_pct": ("tank_level_pct", "%"),
    "tank_level_percent": ("tank_level_pct", "%"),
    "tank_distance_cm": ("tank_distance_cm", "cm"),

    # Environmental & Auxiliary (Context Sensors)
    "temperature_c": ("temperature_c", "°C"),
    "temperature": ("temperature_c", "°C"),
    "humidity_pct": ("humidity_pct", "%"),
    "humidity": ("humidity_pct", "%"),
    "occupancy_count": ("occupancy_count", "count"),
    "occupancy": ("occupancy_count", "count"),
    "air_quality_aqi": ("air_quality_aqi", "AQI"),
    "air_aqi": ("air_quality_aqi", "AQI"),
    "co2_ppm": ("co2_ppm", "ppm"),
    "hvac_load_kw": ("hvac_load_kw", "kW"),
    "hvac_power_kw": ("hvac_load_kw", "kW")
}

# Plausible range limits for physical sanity checking
METRIC_RANGE_LIMITS: Dict[str, Tuple[float, float]] = {
    "cumulative_energy_kwh": (0.0, 1e9),
    "active_power_kw": (0.0, 25000.0),
    "voltage_v": (0.0, 1000.0),
    "voltage_l1_v": (0.0, 1000.0),
    "voltage_l2_v": (0.0, 1000.0),
    "voltage_l3_v": (0.0, 1000.0),
    "current_a": (0.0, 5000.0),
    "current_l1_a": (0.0, 5000.0),
    "current_l2_a": (0.0, 5000.0),
    "current_l3_a": (0.0, 5000.0),
    "power_factor": (0.0, 1.0),
    "frequency_hz": (40.0, 70.0),
    "maximum_demand_kw": (0.0, 25000.0),
    "maximum_demand_kva": (0.0, 30000.0),
    "thd_voltage_pct": (0.0, 100.0),
    "thd_current_pct": (0.0, 100.0),
    "unbalance_voltage_pct": (0.0, 100.0),
    "unbalance_current_pct": (0.0, 100.0),
    "water_flow_lmin": (0.0, 10000.0),
    "cumulative_water_m3": (0.0, 1e8),
    "water_pressure_bar": (0.0, 50.0),
    "water_pressure_kpa": (0.0, 5000.0),
    "tank_level_pct": (0.0, 100.0),
    "tank_distance_cm": (0.0, 1000.0),
    "temperature_c": (-30.0, 85.0),
    "humidity_pct": (0.0, 100.0),
    "occupancy_count": (0, 100000),
    "air_quality_aqi": (0.0, 1000.0),
    "co2_ppm": (200.0, 10000.0),
    "hvac_load_kw": (0.0, 10000.0)
}


class CanonicalMetric(BaseModel):
    metric: str
    value: float
    unit: str
    quality: MetricQuality = MetricQuality.GOOD
    raw_metric: Optional[str] = None

    @property
    def name(self) -> str:
        return self.metric

    @field_validator("value")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Metric value must be a finite numerical number.")
        return v


class TelemetryEnvelope(BaseModel):
    schema_version: str = "1.0"
    message_id: str = Field(default_factory=lambda: f"MSG_{uuid.uuid4().hex[:12].upper()}")
    gateway_id: Optional[str] = None
    simulator_id: Optional[str] = None
    device_id: str
    facility_id: str = "FAC_GEC_CAMPUS"
    building_id: str = "Block B Hostel"
    source_type: SourceType = SourceType.SIMULATED_IOT
    event_timestamp: Optional[str] = None
    sent_timestamp: str
    sequence_number: int = 1
    metrics: List[CanonicalMetric] = Field(default_factory=list)
    is_valid_timestamp: bool = True
    timestamp_error: Optional[str] = None

    @field_validator("device_id")
    @classmethod
    def check_device_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("device_id is required and cannot be empty.")
        return v.strip()


def resolve_provenance_badge(source_type: SourceType, is_verified: bool = True) -> str:
    """Returns canonical display badge for a data source provenance."""
    if source_type == SourceType.REAL_SENSOR:
        return "[REAL SENSOR]" if is_verified else "[UNVERIFIED SENSOR - DEMO MODE]"
    elif source_type == SourceType.SIMULATED_IOT:
        return "[SIMULATED IoT]"
    elif source_type == SourceType.SYNTHETIC:
        return "[SYNTHETIC IoT DATA]"
    elif source_type == SourceType.DERIVED:
        return "[DERIVED BASELINE]"
    elif source_type == SourceType.PREDICTED:
        return "[ML PREDICTED]"
    return "[SIMULATED IoT]"


def normalize_source_type(raw_source: Optional[str], default: SourceType = SourceType.SIMULATED_IOT) -> SourceType:
    """Normalizes arbitrary source_type strings to canonical SourceType."""
    if not raw_source:
        return default
    s = str(raw_source).strip().lower()
    if s in ["real", "real_sensor", "real-sensor", "physical", "live_hardware_mqtt", "hardware", "observed"]:
        return SourceType.REAL_SENSOR
    if s in ["simulated", "simulated_iot", "simulated-iot", "simulator", "sim"]:
        return SourceType.SIMULATED_IOT
    if s in ["synthetic", "synthetic_data", "synthetic-data"]:
        return SourceType.SYNTHETIC
    if s in ["derived", "calculated"]:
        return SourceType.DERIVED
    if s in ["predicted", "forecast"]:
        return SourceType.PREDICTED
    return default


def normalize_telemetry_payload(payload: Dict[str, Any], default_source: Optional[SourceType] = None) -> Tuple[TelemetryEnvelope, Dict[str, Any], List[str]]:
    """
    Normalizes arbitrary inbound HTTP/MQTT payloads into a validated TelemetryEnvelope.
    Extracts metrics from 'metrics' array, 'measurements' object, 'reading' object, or flat fields.
    Returns: (envelope, flat_metrics_map, validation_warnings)
    Raises ValueError on fatal schema or range errors.
    """
    warnings: List[str] = []
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. Determine IDs
    device_id = payload.get("device_id")
    if not device_id:
        # Check topic or nested metadata
        device_id = payload.get("id") or payload.get("meter_id")
    if not device_id:
        raise ValueError("Missing required 'device_id' in telemetry payload.")
    device_id = str(device_id).strip()

    gateway_id = payload.get("gateway_id") or payload.get("simulator_id") or payload.get("instance_id")
    if not gateway_id:
        gateway_id = f"GW_{device_id}"

    facility_id = payload.get("facility_id") or "FAC_GEC_CAMPUS"
    building_id = payload.get("building_id") or "Block B Hostel"

    # 2. Source provenance
    source_str = payload.get("source_type") or payload.get("provenance") or payload.get("data_source")
    source_type = normalize_source_type(source_str, default=default_source or SourceType.SIMULATED_IOT)

    # 3. Timestamps & Clock Skew Policy
    raw_event_ts = payload.get("event_timestamp") or payload.get("timestamp")
    sent_ts = payload.get("sent_timestamp") or now_utc
    is_valid_timestamp = True
    timestamp_error = None
    event_ts = None

    MAX_FUTURE_SKEW_SEC = 300.0  # 5 minutes maximum allowed future clock drift
    MAX_STALE_AGE_HOURS = 720.0  # 30 days maximum past age
    now_dt = datetime.datetime.now(datetime.timezone.utc)

    if raw_event_ts is None or str(raw_event_ts).strip() == "":
        if source_type == SourceType.REAL_SENSOR:
            is_valid_timestamp = False
            timestamp_error = "MISSING_EVENT_TIMESTAMP: Real sensor payload must specify a valid event_timestamp."
            warnings.append(timestamp_error)
            event_ts = None
        else:
            # Simulated telemetry defaults to current UTC time if omitted
            event_ts = now_utc
    else:
        # Parse and validate ISO timestamp without replacing invalid with 'now'
        try:
            clean_ts = str(raw_event_ts).strip().replace("Z", "+00:00")
            pd_ts = datetime.datetime.fromisoformat(clean_ts)
            if pd_ts.tzinfo is None:
                local_epoch = pd_ts.timestamp()
                utc_epoch = pd_ts.replace(tzinfo=datetime.timezone.utc).timestamp()
                now_epoch = datetime.datetime.now().timestamp()
                if abs(local_epoch - now_epoch) <= abs(utc_epoch - now_epoch):
                    pd_ts = pd_ts.astimezone()
                else:
                    pd_ts = pd_ts.replace(tzinfo=datetime.timezone.utc)

            pd_ts_utc = pd_ts.astimezone(datetime.timezone.utc)

            future_diff_sec = (pd_ts_utc - now_dt).total_seconds()
            if future_diff_sec > MAX_FUTURE_SKEW_SEC:
                is_valid_timestamp = False
                timestamp_error = f"FUTURE_EVENT_TIMESTAMP: Timestamp is {future_diff_sec:.1f}s in future beyond {MAX_FUTURE_SKEW_SEC}s permitted clock skew."
                warnings.append(timestamp_error)
                event_ts = str(raw_event_ts)
            else:
                age_hours = (now_dt - pd_ts_utc).total_seconds() / 3600.0
                if age_hours > MAX_STALE_AGE_HOURS:
                    warnings.append(f"Timestamp is very old ({age_hours:.1f} hours in the past).")
                event_ts = pd_ts_utc.isoformat().replace("+00:00", "Z")
        except Exception as e:
            is_valid_timestamp = False
            timestamp_error = f"MALFORMED_EVENT_TIMESTAMP: Could not parse '{raw_event_ts}' as ISO 8601: {str(e)}"
            warnings.append(timestamp_error)
            event_ts = str(raw_event_ts)

    # 4. Message ID & Sequence
    message_id = payload.get("message_id")
    if not message_id:
        seq = payload.get("sequence_number") or payload.get("sequence") or 1
        message_id = f"MSG_{device_id}_{seq}_{int(datetime.datetime.now().timestamp() * 1000)}"

    sequence_num = payload.get("sequence_number") or payload.get("sequence") or 1
    try:
        sequence_num = int(sequence_num)
    except Exception:
        sequence_num = 1

    # 5. Extract Metrics from various incoming conventions
    raw_metric_pairs: List[Tuple[str, Any, Optional[str], MetricQuality]] = []

    # Case A: Canonical list of dicts: "metrics": [{"name": "...", "value": ...}] or [{"metric": "...", "value": ...}]
    if "metrics" in payload and isinstance(payload["metrics"], list):
        for m in payload["metrics"]:
            if isinstance(m, dict) and ("name" in m or "metric" in m) and "value" in m:
                m_name = m.get("name") or m.get("metric")
                q_val = MetricQuality.GOOD
                if "quality" in m:
                    try:
                        q_val = MetricQuality(str(m["quality"]).lower())
                    except Exception:
                        q_val = MetricQuality.GOOD
                raw_metric_pairs.append((str(m_name), m["value"], m.get("unit"), q_val))

    # Case B: Hardware protocol "measurements": {"voltage_v": 231.5, ...}
    if "measurements" in payload and isinstance(payload["measurements"], dict):
        for k, v in payload["measurements"].items():
            raw_metric_pairs.append((k, v, None, MetricQuality.GOOD))

    # Case C: Simulator "reading" or "telemetry": {"active_power_kw": 145.2, ...}
    for subkey in ["reading", "telemetry", "sensors"]:
        if subkey in payload and isinstance(payload[subkey], dict):
            for k, v in payload[subkey].items():
                raw_metric_pairs.append((k, v, None, MetricQuality.GOOD))

    # Case D: Flat payload: {"active_power_kw": 145.2, "energy_kwh": 36.3}
    for k, v in payload.items():
        if k in CANONICAL_METRIC_MAP and isinstance(v, (int, float)):
            raw_metric_pairs.append((k, v, None, MetricQuality.GOOD))

    if not raw_metric_pairs:
        raise ValueError("Telemetry payload contains no parseable sensor metrics.")

    # 6. Normalize and validate each metric
    canonical_metrics: List[CanonicalMetric] = []
    flat_map: Dict[str, float] = {}

    for raw_name, val, raw_unit, quality in raw_metric_pairs:
        # Check finite numerical value
        try:
            num_val = float(val)
        except (TypeError, ValueError):
            warnings.append(f"Ignored non-numeric metric '{raw_name}' with value '{val}'.")
            continue

        if math.isnan(num_val) or math.isinf(num_val):
            raise ValueError(f"Metric '{raw_name}' contains non-finite value '{val}'.")

        raw_lower = raw_name.strip().lower()
        if raw_lower in CANONICAL_METRIC_MAP:
            can_name, can_unit = CANONICAL_METRIC_MAP[raw_lower]
        else:
            # Pass-through unrecognized metric with given unit
            can_name = raw_lower
            can_unit = raw_unit or ""

        # Unit conversions if necessary
        # e.g., if water cumulative is in liters, convert to m3
        if can_name == "cumulative_water_m3" and raw_unit and str(raw_unit).lower() in ["l", "liters", "litre", "litres"]:
            num_val = round(num_val / 1000.0, 4)
            warnings.append("Converted cumulative water from liters to m³.")

        # Range verification
        if can_name in METRIC_RANGE_LIMITS:
            min_lim, max_lim = METRIC_RANGE_LIMITS[can_name]
            if num_val < min_lim or num_val > max_lim:
                raise ValueError(
                    f"Metric '{can_name}' value {num_val} is outside plausible physical range [{min_lim}, {max_lim}] {can_unit}."
                )

        # Avoid duplicates within same envelope: keep latest
        existing_idx = next((i for i, m in enumerate(canonical_metrics) if m.metric == can_name), None)
        can_metric = CanonicalMetric(
            metric=can_name,
            value=round(num_val, 4),
            unit=can_unit,
            quality=quality,
            raw_metric=raw_name if raw_name != can_name else None
        )

        if existing_idx is not None:
            canonical_metrics[existing_idx] = can_metric
        else:
            canonical_metrics.append(can_metric)

        flat_map[can_name] = round(num_val, 4)

    # Keep interval energy separate from cumulative meter totalizers.
    if "water_flow_lmin" in flat_map and "water_flow_lpm" not in flat_map:
        flat_map["water_flow_lpm"] = flat_map["water_flow_lmin"]
    if "cumulative_water_m3" in flat_map and "water_total_m3" not in flat_map:
        flat_map["water_total_m3"] = flat_map["cumulative_water_m3"]

    envelope = TelemetryEnvelope(
        schema_version=payload.get("schema_version", "1.0"),
        message_id=str(message_id),
        gateway_id=str(gateway_id),
        simulator_id=str(gateway_id),
        device_id=str(device_id),
        facility_id=str(facility_id),
        building_id=str(building_id),
        source_type=source_type,
        event_timestamp=str(event_ts) if event_ts is not None else None,
        sent_timestamp=str(sent_ts),
        sequence_number=sequence_num,
        metrics=canonical_metrics,
        is_valid_timestamp=is_valid_timestamp,
        timestamp_error=timestamp_error
    )

    return envelope, flat_map, warnings
