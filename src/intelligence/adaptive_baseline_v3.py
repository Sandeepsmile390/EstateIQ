"""Adaptive Seasonal Energy Baseline for EstateIQ-DIF V3.

Solves seasonal climate drift while strictly preserving leakage boundaries:
- Fits pre-trained robust weekly median and MAD profiles on historical training data.
- During streaming operation, smoothly adapts to seasonal warming using preceding nominal data.
- Strict Anomaly Gating: Readings confirmed or suspected as anomalies or sensor faults
  are NEVER absorbed into the baseline buffer.
- Robust Fallback: Reverts to pre-trained static profiles whenever rolling history is sparse.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.intelligence.seasonal_baseline import BaselineEstimate, SeasonalBaselineModel


class AdaptiveSeasonalBaselineModel:
    """Adaptive 4-Week Rolling Seasonal Slot Baseline with Strict Anomaly Gating."""

    def __init__(
        self,
        window_weeks: int = 4,
        min_observations: int = 2,
        relative_scale_floor: float = 0.05,
        absolute_scale_floor_kwh: float = 0.5,
    ):
        self.window_weeks = window_weeks
        self.min_observations = min_observations
        self.relative_scale_floor = relative_scale_floor
        self.absolute_scale_floor_kwh = absolute_scale_floor_kwh

        # Underlying static baseline (trained on training slice)
        self.static_baseline = SeasonalBaselineModel(
            min_observations=min_observations,
            relative_scale_floor=relative_scale_floor,
            absolute_scale_floor_kwh=absolute_scale_floor_kwh,
        )

        # Dynamic rolling buffers: (building_id, dow, hour, quarter) -> deque of recent nominal kWh
        self._slot_buffers: Dict[Tuple[str, int, int, int], deque] = {}
        self._last_seen_ts: Dict[str, pd.Timestamp] = {}
        self._fitted = False

    def fit(self, history: pd.DataFrame) -> "AdaptiveSeasonalBaselineModel":
        """Fits static reference baseline on clean training slice."""
        self.static_baseline.fit(history)
        self._fitted = True
        self._slot_buffers.clear()
        self._last_seen_ts.clear()

        # Seed the rolling buffers with the last observations from the training history
        dow, hour, quarter = SeasonalBaselineModel._slot_components(history["timestamp"])
        energy_col = next((c for c in ("electricity_kwh", "energy_kwh") if c in history.columns), "electricity_kwh")
        bld_col = history["building_id"].astype(str) if "building_id" in history.columns else pd.Series("default", index=history.index)

        temp_df = pd.DataFrame({
            "bld": bld_col, "dow": dow, "hour": hour, "quarter": quarter,
            "energy": history[energy_col], "ts": pd.to_datetime(history["timestamp"], utc=True)
        }).sort_values("ts")

        for bld_id, bld_grp in temp_df.groupby("bld"):
            self._last_seen_ts[str(bld_id)] = bld_grp["ts"].max()

        for key, grp in temp_df.groupby(["bld", "dow", "hour", "quarter"]):
            k = (str(key[0]), int(key[1]), int(key[2]), int(key[3]))
            buf = deque(maxlen=self.window_weeks)
            for val in grp["energy"].iloc[-self.window_weeks:].values:
                if np.isfinite(val) and val >= 0:
                    buf.append(float(val))
            self._slot_buffers[k] = buf

        return self

    def predict(self, building_id: str, timestamp: str) -> BaselineEstimate:
        """Predicts expected kWh and robust scale using dynamic rolling slot buffer with static fallback."""
        ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
        if pd.isna(ts) or not self._fitted:
            return BaselineEstimate(expected_kwh=15.0, scale_kwh=2.0, observations=0, source="HEURISTIC_FALLBACK")

        key = (str(building_id or "default"), int(ts.dayofweek), int(ts.hour), int((ts.minute // 15) * 15))
        buf = self._slot_buffers.get(key)

        if buf and len(buf) >= self.min_observations:
            vals = np.array(buf, dtype=float)
            med = float(np.median(vals))
            mad = float(np.median(np.abs(vals - med)))
            scale = max(1.4826 * mad, med * self.relative_scale_floor, self.absolute_scale_floor_kwh)
            return BaselineEstimate(
                expected_kwh=med,
                scale_kwh=scale,
                observations=len(vals),
                source="ADAPTIVE_ROLLING_SLOT_MAD",
            )

        # Fallback to pre-trained static profile
        static_est = self.static_baseline.predict(building_id, timestamp)
        if static_est:
            return static_est

        return BaselineEstimate(expected_kwh=15.0, scale_kwh=2.0, observations=0, source="GLOBAL_FALLBACK")

    def update(
        self,
        building_id: str,
        timestamp: str,
        actual_kwh: float,
        is_anomaly: bool,
    ) -> bool:
        """Updates slot history IF AND ONLY IF reading is nominal and chronological.
        
        Returns:
            bool: True if buffer was successfully updated with nominal data, False otherwise.
        """
        if is_anomaly or actual_kwh <= 0.001 or not np.isfinite(actual_kwh):
            # Anomaly or sensor fault detected: DO NOT CONTAMINATE BASELINE
            return False

        ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
        if pd.isna(ts):
            return False

        bld = str(building_id or "default")
        # Ensure chronological update order per building (reject out-of-order and duplicates)
        last_ts = self._last_seen_ts.get(bld)
        if last_ts is not None and ts <= last_ts:
            return False

        self._last_seen_ts[bld] = ts

        key = (bld, int(ts.dayofweek), int(ts.hour), int((ts.minute // 15) * 15))
        buf = self._slot_buffers.setdefault(key, deque(maxlen=self.window_weeks))
        buf.append(float(actual_kwh))
        return True

