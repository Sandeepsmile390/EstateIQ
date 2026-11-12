"""Sensor Health & Data Quality Monitor for EstateIQ V3.

Separates physical sensor faults (communication dropouts, frozen registers, ADC flatlines,
stale telemetry, corrupted values, and out-of-order/duplicate packets)
from building operational and equipment degradation anomalies.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Union
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SensorHealthResult:
    """Outcome of sensor health and telemetry integrity screening."""
    is_sensor_fault: bool
    sensor_fault_type: Optional[str]  # "meter_flatline" | "meter_dropout" | "invalid_reading" | "out_of_order" | "duplicate" | "stale_reading" | None
    confidence: float
    reason: str


class SensorHealthEngine:
    """Monitors telemetry streams for physical meter failure, packet anomalies, and communication loss."""

    def __init__(
        self,
        min_flatline_intervals: int = 4,
        min_stale_intervals: int = 8,
        dropout_hour_start: int = 8,
        dropout_hour_end: int = 19,
    ):
        self.min_flatline_intervals = min_flatline_intervals
        self.min_stale_intervals = min_stale_intervals
        self.dropout_hour_start = dropout_hour_start
        self.dropout_hour_end = dropout_hour_end
        self._buffers: Dict[str, deque] = {}
        self._last_timestamps: Dict[str, pd.Timestamp] = {}

    def evaluate(
        self,
        building_id: str,
        timestamp: Union[str, pd.Timestamp, int],
        actual_kwh: float,
    ) -> SensorHealthResult:
        """Evaluates single-reading telemetry for hardware faults, corruption, or communication loss."""
        bld = str(building_id or "default")

        # 1. Invalid Value Check (NaN, Inf, negative)
        if actual_kwh is None or not np.isfinite(actual_kwh) or actual_kwh < 0.0:
            return SensorHealthResult(
                is_sensor_fault=True,
                sensor_fault_type="invalid_reading",
                confidence=1.0,
                reason=f"Telemetry contains invalid/corrupt numeric value: {actual_kwh}",
            )

        # Parse timestamp
        hour = 12
        if isinstance(timestamp, (int, float)):
            hour = int(timestamp) % 24
            ts = None
        else:
            ts = pd.to_datetime(timestamp, errors="coerce")
            if pd.isna(ts):
                return SensorHealthResult(
                    is_sensor_fault=True,
                    sensor_fault_type="invalid_reading",
                    confidence=1.0,
                    reason=f"Corrupt or unparseable timestamp: {timestamp}",
                )
            if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                ts = ts.tz_convert("Asia/Kolkata")
            hour = int(ts.hour)

        # 2. Chronological Integrity Check (out-of-order and duplicates)
        if ts is not None:
            last_ts = self._last_timestamps.get(bld)
            if last_ts is not None:
                if ts == last_ts:
                    return SensorHealthResult(
                        is_sensor_fault=True,
                        sensor_fault_type="duplicate",
                        confidence=1.0,
                        reason=f"Duplicate packet received at {ts.isoformat()}",
                    )
                if ts < last_ts:
                    return SensorHealthResult(
                        is_sensor_fault=True,
                        sensor_fault_type="out_of_order",
                        confidence=1.0,
                        reason=f"Out-of-order packet: {ts.isoformat()} arrived after {last_ts.isoformat()}",
                    )
            self._last_timestamps[bld] = ts

        # Buffer recent readings
        buf = self._buffers.setdefault(bld, deque(maxlen=self.min_stale_intervals))
        buf.append(float(actual_kwh))

        # 3. Meter Dropout Detection: Zero/near-zero reading during active daytime operational hours
        if (self.dropout_hour_start <= hour <= self.dropout_hour_end) and actual_kwh <= 0.001:
            return SensorHealthResult(
                is_sensor_fault=True,
                sensor_fault_type="meter_dropout",
                confidence=0.95,
                reason=f"Telemetry dropped to {actual_kwh:.3f} kWh during active daytime operational hours ({hour}:00)",
            )

        # 4. Meter Flatline & Stale Telemetry Detection: Invariant reading across consecutive intervals
        if len(buf) >= self.min_flatline_intervals:
            recent_vals = list(buf)[-self.min_flatline_intervals:]
            if actual_kwh > 0.05:  # Not standby off
                variance = float(np.var(recent_vals))
                if variance < 1e-6:
                    # Check if extended stale
                    if len(buf) >= self.min_stale_intervals and float(np.var(list(buf))) < 1e-7:
                        return SensorHealthResult(
                            is_sensor_fault=True,
                            sensor_fault_type="stale_reading",
                            confidence=0.99,
                            reason=f"Sensor telemetry is completely stale: invariant {actual_kwh:.3f} kWh across {len(buf)} intervals",
                        )
                    return SensorHealthResult(
                        is_sensor_fault=True,
                        sensor_fault_type="meter_flatline",
                        confidence=0.98,
                        reason=f"Sensor ADC register frozen at exactly {actual_kwh:.3f} kWh for {self.min_flatline_intervals} intervals",
                    )

        return SensorHealthResult(
            is_sensor_fault=False,
            sensor_fault_type=None,
            confidence=1.0,
            reason="Telemetry exhibits expected physical dynamic variance",
        )

    def reset(self, building_id: Optional[str] = None) -> None:
        """Resets buffer and timestamp state for building or entire facility."""
        if building_id:
            self._buffers.pop(building_id, None)
            self._last_timestamps.pop(building_id, None)
        else:
            self._buffers.clear()
            self._last_timestamps.clear()

