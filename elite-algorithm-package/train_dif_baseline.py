"""Fit a leakage-conscious DIF seasonal baseline from a declared past period.

Example:
  python train_dif_baseline.py --input facility_dataset/data/raw/energy_readings.csv \
      --train-through 2026-10-01T00:00:00+05:30 --output models/dif_baseline.json
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.intelligence.seasonal_baseline import SeasonalBaselineModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit an Elite-DIF building/slot seasonal median-MAD baseline.")
    parser.add_argument("--input", required=True, type=Path, help="CSV with timestamp, building_id and energy values")
    parser.add_argument("--train-through", required=True, help="Exclusive timestamp cutoff with timezone")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON baseline artifact")
    parser.add_argument("--min-observations", type=int, default=8)
    args = parser.parse_args()

    cutoff = pd.Timestamp(args.train_through)
    if cutoff.tzinfo is None:
        parser.error("--train-through must include an explicit timezone offset")
    frame = pd.read_csv(args.input, usecols=lambda c: c in {"timestamp", "building_id", "electricity_kwh", "energy_kwh"},
                        parse_dates=["timestamp"])
    timestamps_utc = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.loc[timestamps_utc < cutoff.tz_convert("UTC")].copy()
    if frame.empty:
        parser.error("no telemetry rows precede --train-through")
    model = SeasonalBaselineModel(min_observations=args.min_observations).fit(frame)
    model.save(args.output)
    print(f"Saved {model.profile_count} seasonal profiles from {model.training_rows} pre-cutoff rows; training_end={model.training_end} UTC")
    print(f"Artifact: {args.output.resolve()}")


if __name__ == "__main__":
    main()
