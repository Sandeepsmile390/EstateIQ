"""Leakage-conscious seasonal energy baseline for EstateIQ-DIF.

The model learns a robust reference per building and 15-minute slot of the
week. It intentionally ignores anomaly labels and must be fitted on the
training history only. Callers can retain the fitted model and reuse it for
streaming inference.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BaselineEstimate:
    expected_kwh: float
    scale_kwh: float
    observations: int
    source: str


class SeasonalBaselineModel:
    """Robust seasonal median baseline with a MAD-based scale estimate."""

    _ENERGY_COLUMNS = ("electricity_kwh", "energy_kwh")

    def __init__(self, min_observations: int = 8, relative_scale_floor: float = 0.05,
                 absolute_scale_floor_kwh: float = 0.5):
        if min_observations < 2:
            raise ValueError("min_observations must be at least 2")
        if not 0.0 < relative_scale_floor <= 1.0:
            raise ValueError("relative_scale_floor must be in (0, 1]")
        if absolute_scale_floor_kwh <= 0.0:
            raise ValueError("absolute_scale_floor_kwh must be positive")
        self.min_observations = int(min_observations)
        self.relative_scale_floor = float(relative_scale_floor)
        self.absolute_scale_floor_kwh = float(absolute_scale_floor_kwh)
        self._profiles: Dict[Tuple[str, int, int, int], BaselineEstimate] = {}
        self._fitted = False
        self.training_rows = 0
        self.training_end: Optional[str] = None

    @staticmethod
    def _slot_components(timestamps: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ts = pd.to_datetime(timestamps, utc=True, errors="coerce")
        return ts.dt.dayofweek, ts.dt.hour, (ts.dt.minute // 15) * 15

    def fit(self, history: pd.DataFrame) -> "SeasonalBaselineModel":
        """Fit on historical telemetry; label columns are never read or used."""
        if history is None or history.empty:
            raise ValueError("history must contain training telemetry")
        energy_col = next((c for c in self._ENERGY_COLUMNS if c in history.columns), None)
        if energy_col is None or "timestamp" not in history.columns:
            raise ValueError("history requires timestamp and electricity_kwh or energy_kwh")

        building = history["building_id"].astype(str) if "building_id" in history.columns else pd.Series("*", index=history.index)
        dow, hour, quarter = self._slot_components(history["timestamp"])
        values = pd.to_numeric(history[energy_col], errors="coerce")
        clean = pd.DataFrame({"building": building, "dow": dow, "hour": hour,
                              "quarter": quarter, "energy": values})
        clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
        clean = clean[clean["energy"] >= 0]
        if clean.empty:
            raise ValueError("history has no finite non-negative energy observations")

        profiles: Dict[Tuple[str, int, int, int], BaselineEstimate] = {}
        for key, group in clean.groupby(["building", "dow", "hour", "quarter"], sort=False):
            values = group["energy"].to_numpy(dtype=float)
            if len(values) < self.min_observations:
                continue
            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))
            robust_scale = 1.4826 * mad
            scale = max(robust_scale, abs(median) * self.relative_scale_floor,
                        self.absolute_scale_floor_kwh)
            profiles[(str(key[0]), int(key[1]), int(key[2]), int(key[3]))] = BaselineEstimate(
                expected_kwh=median, scale_kwh=scale,
                observations=len(values), source="SEASONAL_MEDIAN_MAD")

        if not profiles:
            raise ValueError("no seasonal slot has enough training observations")
        self._profiles = profiles
        self._fitted = True
        self.training_rows = len(clean)
        self.training_end = pd.to_datetime(history["timestamp"], utc=True, errors="coerce").max().isoformat()
        return self

    def predict(self, building_id: str, timestamp: str) -> Optional[BaselineEstimate]:
        """Return a pre-fitted estimate for one event, or None for cold start."""
        if not self._fitted:
            return None
        ts = pd.to_datetime(timestamp, utc=True, errors="coerce")
        if pd.isna(ts):
            return None
        key = (str(building_id or "*"), int(ts.dayofweek), int(ts.hour), int((ts.minute // 15) * 15))
        return self._profiles.get(key) or self._profiles.get(("*", *key[1:]))

    def save(self, path: Path) -> None:
        """Persist the fitted profile as a portable, inspectable JSON artifact."""
        if not self._fitted:
            raise RuntimeError("fit the baseline model before saving")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "min_observations": self.min_observations,
            "relative_scale_floor": self.relative_scale_floor,
            "absolute_scale_floor_kwh": self.absolute_scale_floor_kwh,
            "training_rows": self.training_rows,
            "training_end": self.training_end,
            "profiles": [
                {"building_id": k[0], "day_of_week_utc": k[1], "hour_utc": k[2],
                 "quarter_minute_utc": k[3], "expected_kwh": v.expected_kwh,
                 "scale_kwh": v.scale_kwh, "observations": v.observations,
                 "source": v.source}
                for k, v in sorted(self._profiles.items())
            ],
        }
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
        temp_path.replace(path)

    @classmethod
    def load(cls, path: Path) -> "SeasonalBaselineModel":
        """Load a previously fitted and versioned JSON profile artifact."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported seasonal baseline schema version")
        model = cls(
            min_observations=int(payload["min_observations"]),
            relative_scale_floor=float(payload["relative_scale_floor"]),
            absolute_scale_floor_kwh=float(payload["absolute_scale_floor_kwh"]),
        )
        profiles = {}
        for row in payload["profiles"]:
            estimate = BaselineEstimate(
                expected_kwh=float(row["expected_kwh"]), scale_kwh=float(row["scale_kwh"]),
                observations=int(row["observations"]), source=str(row["source"]),
            )
            if (not np.isfinite(estimate.expected_kwh) or not np.isfinite(estimate.scale_kwh)
                    or estimate.scale_kwh <= 0 or estimate.observations < model.min_observations):
                raise ValueError("invalid profile in seasonal baseline artifact")
            key = (str(row["building_id"]), int(row["day_of_week_utc"]),
                   int(row["hour_utc"]), int(row["quarter_minute_utc"]))
            profiles[key] = estimate
        if not profiles:
            raise ValueError("seasonal baseline artifact has no profiles")
        model._profiles = profiles
        model._fitted = True
        model.training_rows = int(payload["training_rows"])
        model.training_end = payload.get("training_end")
        return model

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def profile_count(self) -> int:
        return len(self._profiles)

