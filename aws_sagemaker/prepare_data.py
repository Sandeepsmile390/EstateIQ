"""Create leakage-aware SageMaker channels from EstateIQ synthetic energy data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "facility_dataset/data/synthetic_model_training/energy_readings_model_training.csv"
DEFAULT_OUTPUT = ROOT / "output/sagemaker/estateiq_anomaly_v1"
HOLDOUT_BUILDING = "BLD004"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(source: Path, output: Path, train_end: str, validation_end: str,
            holdout_building: str = HOLDOUT_BUILDING) -> dict[str, Any]:
    frame = pd.read_csv(source)
    required = {"timestamp", "building_id", "electricity_kwh", "fault_category"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")
    frame["_timestamp_utc"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["_timestamp_utc", "building_id", "fault_category"]).copy()

    # This energy model learns building faults only. Sensor faults belong to the
    # separate EstateIQ sensor-health monitor and are excluded from this target.
    frame = frame[frame["fault_category"].isin(["nominal", "building_fault"])].copy()
    frame["target_anomaly"] = (frame["fault_category"] == "building_fault").astype("int8")
    train_cut = pd.Timestamp(train_end)
    validation_cut = pd.Timestamp(validation_end)
    if train_cut.tzinfo is None or validation_cut.tzinfo is None:
        raise ValueError("Split cutoffs must include a UTC offset, e.g. 2026-03-15T23:45:00+05:30")
    train_cut = train_cut.tz_convert("UTC")
    validation_cut = validation_cut.tz_convert("UTC")
    if validation_cut <= train_cut:
        raise ValueError("validation-end must be later than train-end")

    seen_buildings = frame[frame["building_id"].astype(str) != holdout_building].copy()
    unseen_building = frame[frame["building_id"].astype(str) == holdout_building].copy()
    if unseen_building.empty:
        raise ValueError(f"Configured held-out building {holdout_building!r} has no rows")

    splits = {
        "train": seen_buildings[seen_buildings["_timestamp_utc"] <= train_cut],
        "validation": seen_buildings[(seen_buildings["_timestamp_utc"] > train_cut) & (seen_buildings["_timestamp_utc"] <= validation_cut)],
        "test": seen_buildings[seen_buildings["_timestamp_utc"] > validation_cut],
        # Entirely unseen building; never used for fitting or threshold calibration.
        "building_holdout": unseen_building,
    }
    if any(part.empty for part in splits.values()):
        raise ValueError("One or more train/validation/test/holdout splits are empty")
    for name in ("train", "validation", "test"):
        if splits[name]["target_anomaly"].nunique() < 2:
            raise ValueError(f"{name} split must contain nominal and building-fault rows")

    output.mkdir(parents=True, exist_ok=True)
    channel_stats: dict[str, dict[str, Any]] = {}
    # Keep only runtime features, target, timestamp/building/event metadata. Never
    # pass anomaly_type, fault_category, or anomaly_flag to the training process.
    allowed = [
        "timestamp", "building_id", "electricity_kwh", "hvac_kwh", "lighting_kwh",
        "equipment_kwh", "other_kwh", "power_factor", "temperature_c", "occupancy_count",
        "target_anomaly", "event_id",
    ]
    columns = [name for name in allowed if name in frame.columns]
    for name, part in splits.items():
        channel_dir = output / name
        channel_dir.mkdir(parents=True, exist_ok=True)
        exported = part[columns].sort_values(["timestamp", "building_id"]).reset_index(drop=True)
        exported.to_csv(channel_dir / f"{name}.csv", index=False)
        channel_stats[name] = {
            "rows": int(len(exported)),
            "building_fault_rows": int(exported["target_anomaly"].sum()),
            "nominal_rows": int((exported["target_anomaly"] == 0).sum()),
            "buildings": sorted(exported["building_id"].astype(str).unique().tolist()),
            "start_utc": pd.to_datetime(exported["timestamp"], utc=True).min().isoformat(),
            "end_utc": pd.to_datetime(exported["timestamp"], utc=True).max().isoformat(),
        }

    manifest = {
        "dataset": str(source.resolve()),
        "dataset_sha256": sha256_file(source),
        "source_rows": int(len(pd.read_csv(source, usecols=["timestamp"]))),
        "rows_excluded_sensor_quality_faults_and_invalid_timestamps": int(
            len(pd.read_csv(source, usecols=["timestamp"])) - sum(item["rows"] for item in channel_stats.values())
        ),
        "target": "target_anomaly = fault_category == building_fault",
        "excluded_target_sources": ["sensor_quality_fault", "anomaly_type", "anomaly_flag", "fault_category"],
        "held_out_building": holdout_building,
        "train_end_inclusive": train_cut.isoformat(),
        "validation_end_inclusive": validation_cut.isoformat(),
        "channels": channel_stats,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-end", default="2026-03-15T23:45:00+05:30")
    parser.add_argument("--validation-end", default="2026-03-31T23:45:00+05:30")
    parser.add_argument("--holdout-building", default=HOLDOUT_BUILDING)
    args = parser.parse_args()
    manifest = prepare(args.source, args.output, args.train_end, args.validation_end, args.holdout_building)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
