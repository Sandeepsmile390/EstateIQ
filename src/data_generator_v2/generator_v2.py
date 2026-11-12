"""Dataset Generator V2: Physics-Constrained Multi-Building Energy Telemetry Generator.

Generates realistic 15-minute interval energy data for campus facilities:
- Occupancy and weather coupling
- Diurnal and weekly cyclical patterns
- Submeter breakdowns (HVAC, lighting, equipment, base load)
- Multi-mode operational and sensor fault injection
- Clean chronological split architecture:
  * Training Period: Jan 1 - Mar 15 (100% nominal)
  * Validation Period: Mar 16 - Mar 31 (100% nominal, zero test labels)
  * Evaluation Period: Apr 1 - Jun 30 (Contains diverse injected faults)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data_generator_v2.fault_injection import (
    FaultScenario,
    get_canonical_v2_scenarios,
    get_model_training_scenarios,
    inject_fault_scenarios,
)

logger = logging.getLogger("GeneratorV2")


class DatasetGeneratorV2:
    """Orchestrates generation of the versioned synthetic dataset with fault scenarios."""

    def __init__(
        self,
        seed: int = 42,
        start_date: str = "2026-01-01 00:00:00",
        end_date: str = "2026-06-30 23:45:00",
        freq: str = "15min",
        output_dir: Optional[Path] = None,
    ):
        self.seed = seed
        self.start_date = start_date
        self.end_date = end_date
        self.freq = freq
        self.output_dir = output_dir or Path("facility_dataset/data/synthetic_v2")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.buildings = [
            {"building_id": "BLD001", "name": "Academic Block A", "type": "Academic", "area_sqft": 45000, "capacity": 1200, "hvac_type": "VRF_Central", "profile": "academic_daytime"},
            {"building_id": "BLD002", "name": "Academic Block B", "type": "Academic", "area_sqft": 40000, "capacity": 1000, "hvac_type": "VRF_Central", "profile": "academic_daytime"},
            {"building_id": "BLD003", "name": "Computer Science Block", "type": "Academic", "area_sqft": 50000, "capacity": 1500, "hvac_type": "Chiller_FCU", "profile": "academic_extended"},
            {"building_id": "BLD004", "name": "Administration Block", "type": "Admin", "area_sqft": 25000, "capacity": 300, "hvac_type": "Split_AC", "profile": "office_hours"},
            {"building_id": "BLD005", "name": "Library", "type": "Library", "area_sqft": 35000, "capacity": 800, "hvac_type": "Central_AHU", "profile": "library_hours"},
        ]

    def generate_timestamps(self) -> pd.DatetimeIndex:
        return pd.date_range(
            start=pd.Timestamp(self.start_date, tz="Asia/Kolkata"),
            end=pd.Timestamp(self.end_date, tz="Asia/Kolkata"),
            freq=self.freq,
        )

    def generate_ambient_weather(self, timestamps: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
        """Generates realistic diurnal temperature and solar radiation curves."""
        n = len(timestamps)
        hours = timestamps.hour + timestamps.minute / 60.0
        day_of_year = timestamps.dayofyear

        # Seasonal warming from Jan (cool) to May/June (hot summer in India)
        seasonal_trend = 22.0 + 12.0 * np.sin((day_of_year - 40) * np.pi / 180.0)
        # Diurnal swing: peak at 14:00 (2 PM), low at 05:00 (5 AM)
        diurnal_swing = 7.5 * np.sin((hours - 8.0) * np.pi / 12.0)
        noise = rng.normal(0, 0.8, n)
        temp_c = np.round(np.clip(seasonal_trend + diurnal_swing + noise, 12.0, 45.0), 2)

        # Solar radiation
        solar_peak = np.maximum(0.0, np.sin((hours - 6.0) * np.pi / 12.0))
        solar_w_m2 = np.round(solar_peak * 850.0 + rng.normal(0, 20.0, n), 1)
        solar_w_m2 = np.clip(solar_w_m2, 0.0, 1050.0)

        return pd.DataFrame({"timestamp": timestamps, "temperature_c": temp_c, "solar_w_m2": solar_w_m2})

    def simulate_occupancy(
        self,
        bld: Dict[str, Any],
        timestamps: pd.DatetimeIndex,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Simulates schedule-driven occupancy."""
        n = len(timestamps)
        hours = timestamps.hour + timestamps.minute / 60.0
        dows = timestamps.dayofweek
        is_weekend = dows >= 5
        cap = bld["capacity"]
        prof = bld["profile"]

        ratios = np.zeros(n)
        for i in range(n):
            hr = hours[i]
            wknd = is_weekend[i]
            if wknd:
                ratios[i] = 0.04 if hr < 9 or hr > 18 else 0.12
            else:
                if prof == "academic_daytime":
                    if 8.5 <= hr <= 16.5:
                        ratios[i] = 0.70 + 0.15 * np.sin((hr - 8.5) * np.pi / 8.0)
                    elif 16.5 < hr <= 18.0:
                        ratios[i] = 0.30
                    else:
                        ratios[i] = 0.02
                elif prof == "academic_extended":
                    if 8.0 <= hr <= 17.0:
                        ratios[i] = 0.75 + 0.15 * np.sin((hr - 8.0) * np.pi / 9.0)
                    elif 17.0 < hr <= 21.0:
                        ratios[i] = 0.35
                    else:
                        ratios[i] = 0.03
                elif prof == "office_hours":
                    if 9.0 <= hr <= 17.5:
                        ratios[i] = 0.80
                    elif 17.5 < hr <= 19.0:
                        ratios[i] = 0.20
                    else:
                        ratios[i] = 0.01
                elif prof == "library_hours":
                    if 8.0 <= hr <= 21.0:
                        ratios[i] = 0.60 + 0.15 * np.sin((hr - 8.0) * np.pi / 13.0)
                    else:
                        ratios[i] = 0.05

        counts = np.round(ratios * cap + rng.normal(0, cap * 0.02, n))
        return np.clip(counts, 0, cap).astype(int)

    def generate_raw_baseline_readings(self) -> pd.DataFrame:
        """Generates clean uncorrupted baseline energy readings across all buildings."""
        rng = np.random.default_rng(self.seed)
        timestamps = self.generate_timestamps()
        weather_df = self.generate_ambient_weather(timestamps, rng)

        records = []
        for bld in self.buildings:
            bld_id = bld["building_id"]
            area = bld["area_sqft"]
            hvac_type = bld["hvac_type"]
            occ_counts = self.simulate_occupancy(bld, timestamps, rng)

            hours = timestamps.hour + timestamps.minute / 60.0
            temps = weather_df["temperature_c"].values

            # Standby power: ~0.35 kW per 1000 sqft
            base_kw = (area / 1000.0) * 0.35

            hvac_mult = 1.6 if "Chiller" in hvac_type else (1.2 if "VRF" in hvac_type else 0.5)

            for i in range(len(timestamps)):
                ts = timestamps[i]
                hr = hours[i]
                t_c = temps[i]
                occ = occ_counts[i]

                # HVAC load
                hvac_kw = max(0.4, (max(0.0, t_c - 20.0) * 1.8 * hvac_mult + occ * 0.065))

                # Lighting load
                is_night = hr < 7.0 or hr > 18.0
                lighting_kw = max(0.2, (area / 1000.0) * (0.65 if is_night else 0.15) + occ * 0.025)

                # Equipment load
                equip_kw = max(0.5, (area / 1000.0) * 0.40 + occ * 0.10)

                # Other miscellaneous
                other_kw = base_kw + rng.normal(0.4, 0.08)

                # Total load in kW with physical thermal inertia
                total_kw = max(1.5, hvac_kw + lighting_kw + equip_kw + other_kw + rng.normal(0, 0.8))

                # Convert to 15-min kWh (kW * 0.25 hours)
                electricity_kwh = round(total_kw * 0.25, 3)
                hvac_kwh = round(hvac_kw * 0.25, 3)
                lighting_kwh = round(lighting_kw * 0.25, 3)
                equipment_kwh = round(equip_kw * 0.25, 3)
                other_kwh = round(other_kw * 0.25, 3)

                pf_raw = 0.95 - (hvac_kw / (total_kw + 1e-4)) * 0.08 + rng.normal(0, 0.008)
                power_factor = round(float(np.clip(pf_raw, 0.80, 0.99)), 3)

                records.append({
                    "timestamp": ts,
                    "building_id": bld_id,
                    "electricity_kwh": electricity_kwh,
                    "hvac_kwh": hvac_kwh,
                    "lighting_kwh": lighting_kwh,
                    "equipment_kwh": equipment_kwh,
                    "other_kwh": other_kwh,
                    "power_factor": power_factor,
                    "temperature_c": t_c,
                    "occupancy_count": occ,
                })

        df_out = pd.DataFrame(records)
        df_out.sort_values(by=["building_id", "timestamp"], inplace=True)
        df_out.reset_index(drop=True, inplace=True)
        return df_out

    def generate_in_memory(self, scenario_suite: str = "canonical") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Executes generation and fault injection in-memory without overwriting disk artifacts."""
        df_baseline = self.generate_raw_baseline_readings()
        if scenario_suite == "model_training":
            scenarios = get_model_training_scenarios()
        else:
            scenarios = get_canonical_v2_scenarios()
        df_labeled, events_df = inject_fault_scenarios(df_baseline, scenarios, seed=self.seed)
        return df_labeled, events_df

    def generate(self) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Executes complete generation, fault injection, and metadata export."""
        logger.info("Generating clean baseline telemetry (seed=%d)...", self.seed)
        df_labeled, events_df = self.generate_in_memory()

        # Save CSV artifacts
        data_csv_path = self.output_dir / "energy_readings_v2.csv"
        events_csv_path = self.output_dir / "ground_truth_events_v2.csv"
        df_labeled.to_csv(data_csv_path, index=False)
        events_df.to_csv(events_csv_path, index=False)

        # Calculate dataset SHA-256
        hasher = hashlib.sha256()
        with open(data_csv_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        dataset_sha256 = hasher.hexdigest()

        # Build comprehensive metadata
        counts_by_type = df_labeled[df_labeled["anomaly_flag"] == 1]["anomaly_type"].value_counts().to_dict()
        counts_by_bld = df_labeled[df_labeled["anomaly_flag"] == 1]["building_id"].value_counts().to_dict()

        metadata: Dict[str, Any] = {
            "generator_name": "EstateIQ DatasetGeneratorV2",
            "generator_version": "2.0.0",
            "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
            "data_nature": "SYNTHETIC_PHYSICS_CONSTRAINED",
            "random_seed": self.seed,
            "dataset_sha256": dataset_sha256,
            "total_rows": len(df_labeled),
            "total_buildings": len(self.buildings),
            "buildings_evaluated": [b["building_id"] for b in self.buildings],
            "sampling_frequency": self.freq,
            "date_range": {
                "start": str(df_labeled["timestamp"].min()),
                "end": str(df_labeled["timestamp"].max()),
                "total_days": round(len(df_labeled["timestamp"].unique()) * 0.25 / 24.0, 2),
            },
            "split_architecture": {
                "train_period": "2026-01-01 00:00:00 to 2026-03-15 23:45:00 (Nominal, 100% clean)",
                "val_period": "2026-03-16 00:00:00 to 2026-03-31 23:45:00 (Nominal, 100% clean)",
                "test_period": "2026-04-01 00:00:00 to 2026-06-30 23:45:00 (Evaluated, contains all injected events)",
            },
            "ground_truth_summary": {
                "total_events": len(events_df),
                "total_anomalous_intervals": int(df_labeled["anomaly_flag"].sum()),
                "nominal_intervals": int((df_labeled["anomaly_flag"] == 0).sum()),
                "anomaly_prevalence_pct": round(float(df_labeled["anomaly_flag"].mean() * 100.0), 3),
                "counts_by_anomaly_type": counts_by_type,
                "counts_by_building": counts_by_bld,
            },
            "schema": {
                "timestamp": "ISO 8601 Datetime with Asia/Kolkata timezone",
                "building_id": "Building identifier (BLD001-BLD005)",
                "electricity_kwh": "Total 15-min interval electricity consumption",
                "hvac_kwh": "HVAC submeter electricity consumption",
                "lighting_kwh": "Lighting submeter electricity consumption",
                "equipment_kwh": "Plug-load equipment submeter consumption",
                "other_kwh": "Base load standby electricity",
                "power_factor": "Electrical power factor (0.80 - 0.99)",
                "temperature_c": "Ambient temperature in Celsius",
                "occupancy_count": "Simulated headcount occupancy",
                "anomaly_flag": "Ground truth binary indicator (0=normal, 1=anomaly)",
                "anomaly_type": "Ground truth classification label",
                "fault_category": "nominal | building_fault | sensor_quality_fault",
                "event_id": "Ground truth event ID (e.g. EVT_V2_001) or 'none'",
            },
            "disclaimer": "All telemetry is synthetic physics-constrained data generated for controlled algorithm benchmarking.",
        }

        meta_path = self.output_dir / "dataset_metadata_v2.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            "Dataset V2 generated successfully: %d rows, %d events, %d positive intervals. Hash: %s",
            len(df_labeled),
            len(events_df),
            int(df_labeled["anomaly_flag"].sum()),
            dataset_sha256[:16],
        )

        return df_labeled, events_df, metadata


def main():
    parser = argparse.ArgumentParser(description="EstateIQ Synthetic Dataset Generator V2")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed (default: 42)")
    parser.add_argument("--output-dir", type=str, default="facility_dataset/data/synthetic_v2", help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    gen = DatasetGeneratorV2(seed=args.seed, output_dir=Path(args.output_dir))
    gen.generate()


if __name__ == "__main__":
    main()

