"""Validation Module for Generator V2 Dataset and Ground-Truth Events.

Enforces physical boundaries, temporal monotonicity, absence of duplicates,
clean split isolation, and exact alignment between event records and pointwise labels.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

logger = logging.getLogger("ValidationV2")


def validate_v2_dataset(
    data_df: pd.DataFrame,
    events_df: pd.DataFrame,
    train_end: str = "2026-03-15 23:45:00",
    val_end: str = "2026-03-31 23:45:00",
) -> Dict[str, Any]:
    """Runs rigorous assertions and validation checks on Generator V2 data."""
    logger.info("Executing comprehensive validation on Generator V2 dataset...")

    errors: List[str] = []

    # 1. Null checks
    null_counts = data_df.isnull().sum()
    if null_counts.sum() > 0:
        errors.append(f"Unexpected NULL values found: {null_counts[null_counts > 0].to_dict()}")

    # 2. Physical ranges
    if (data_df["electricity_kwh"] < 0).any():
        errors.append("Negative electricity_kwh detected!")
    if (data_df["power_factor"] < 0.0).any() or (data_df["power_factor"] > 1.0).any():
        errors.append("Power factor outside valid [0.0, 1.0] range detected!")
    if (data_df["temperature_c"] < -10.0).any() or (data_df["temperature_c"] > 60.0).any():
        errors.append("Temperature outside valid physical range [-10, 60] C detected!")
    if (data_df["occupancy_count"] < 0).any():
        errors.append("Negative occupancy count detected!")

    # 3. Monotonic timestamps & duplicates
    for bld, group in data_df.groupby("building_id"):
        ts = pd.to_datetime(group["timestamp"])
        if not ts.is_monotonic_increasing:
            errors.append(f"Timestamps for building {bld} are not monotonically increasing!")
        dup_count = group.duplicated(subset=["timestamp"]).sum()
        if dup_count > 0:
            errors.append(f"Building {bld} contains {dup_count} duplicate timestamps!")

    # 4. Clean split verification (Zero leakage / zero nominal contamination)
    t_train_end = pd.to_datetime(train_end).tz_localize("Asia/Kolkata")
    t_val_end = pd.to_datetime(val_end).tz_localize("Asia/Kolkata")

    ts_all = pd.to_datetime(data_df["timestamp"])
    train_anomalies = data_df[ts_all <= t_train_end]["anomaly_flag"].sum()
    val_anomalies = data_df[(ts_all > t_train_end) & (ts_all <= t_val_end)]["anomaly_flag"].sum()

    if train_anomalies > 0:
        errors.append(f"Training split contains {train_anomalies} anomalies! Must be 100% nominal.")
    if val_anomalies > 0:
        errors.append(f"Validation split contains {val_anomalies} anomalies! Must be 100% nominal.")

    # 5. Event-to-row alignment
    for _, ev in events_df.iterrows():
        ev_id = ev["event_id"]
        ev_bld = ev["building_id"]
        ev_start = pd.to_datetime(ev["start_timestamp"])
        ev_end = pd.to_datetime(ev["end_timestamp"])
        expected_count = int(ev["interval_count"])

        mask = (
            (data_df["event_id"] == ev_id)
            & (data_df["building_id"] == ev_bld)
            & (data_df["anomaly_flag"] == 1)
        )
        actual_count = int(mask.sum())

        if actual_count != expected_count:
            errors.append(
                f"Event {ev_id} interval count mismatch: expected {expected_count}, found {actual_count} rows in data!"
            )

        # Check timestamp bounds
        matching_rows = data_df[mask]
        if not matching_rows.empty:
            min_ts = pd.to_datetime(matching_rows["timestamp"]).min()
            max_ts = pd.to_datetime(matching_rows["timestamp"]).max()
            if min_ts < ev_start or max_ts > ev_end:
                errors.append(
                    f"Event {ev_id} timestamp out of declared bounds: [{min_ts}, {max_ts}] vs [{ev_start}, {ev_end}]"
                )

    # 6. Unassigned anomalies check
    orphans = data_df[(data_df["anomaly_flag"] == 1) & (data_df["event_id"] == "none")]
    if not orphans.empty:
        errors.append(f"Found {len(orphans)} positive anomaly rows with event_id == 'none'!")

    if errors:
        msg = f"Validation failed with {len(errors)} errors:\n" + "\n".join(f" - {e}" for e in errors)
        logger.error(msg)
        raise ValueError(msg)

    summary = {
        "validation_passed": True,
        "total_rows_validated": len(data_df),
        "total_events_validated": len(events_df),
        "total_anomalies_validated": int(data_df["anomaly_flag"].sum()),
        "train_nominal_verified": True,
        "val_nominal_verified": True,
        "event_row_alignment_verified": True,
    }
    logger.info("Validation successful: all physical and logical constraints verified.")
    return summary

