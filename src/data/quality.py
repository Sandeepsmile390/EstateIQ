"""
Data Quality Validation Module for Sustainable Facility Dashboard.
Implements automated checks for missing data, duplicate timestamps, invalid ranges,
flat-line sensor failures, timestamp gaps, and calculates a overall Data Quality Score (0-100).
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

class DataQualityChecker:
    def __init__(self, df: pd.DataFrame, timestamp_col: str = "timestamp"):
        self.df = df.copy()
        self.timestamp_col = timestamp_col
        if self.timestamp_col in self.df.columns:
            self.df[self.timestamp_col] = pd.to_datetime(self.df[self.timestamp_col])
            
    def check_missing_values(self) -> Dict[str, int]:
        """Checks count of missing values per column."""
        return self.df.isnull().sum().to_dict()

    def check_duplicate_timestamps(self, subset_cols: List[str] = None) -> int:
        """Checks count of duplicate timestamps within facility or entity grouping."""
        cols = [self.timestamp_col]
        if subset_cols:
            for c in subset_cols:
                if c in self.df.columns and c not in cols:
                    cols.append(c)
        else:
            # Auto-detect entity column if present
            for entity_col in ["building_id", "bin_id", "location", "parking_zone", "equipment_id"]:
                if entity_col in self.df.columns and entity_col not in cols:
                    cols.append(entity_col)
                    break
        return int(self.df.duplicated(subset=cols).sum())

    def check_flatline_sensors(self, numeric_cols: List[str], window: int = 12) -> Dict[str, int]:
        """Detects flat-line sensor failures (where values remain strictly constant over a long window)."""
        flatline_counts = {}
        for col in numeric_cols:
            if col in self.df.columns:
                diff = (self.df[col] - self.df[col].shift(1)).abs()
                is_zero_diff = (diff < 1e-5)
                rolling_flat = is_zero_diff.rolling(window=window).sum()
                flatline_counts[col] = int((rolling_flat >= (window - 1)).sum())
        return flatline_counts

    def check_out_of_range(self, range_bounds: Dict[str, tuple]) -> Dict[str, int]:
        """Checks out of range values against known physical min/max bounds."""
        violations = {}
        for col, (min_v, max_v) in range_bounds.items():
            if col in self.df.columns:
                invalid_count = int(((self.df[col] < min_v) | (self.df[col] > max_v)).sum())
                violations[col] = invalid_count
        return violations

    def check_timestamp_gaps(self, expected_freq_minutes: int = 60) -> int:
        """Checks for missing timestamp intervals in continuous time-series data."""
        if self.timestamp_col not in self.df.columns or len(self.df) < 2:
            return 0
        sorted_ts = self.df[self.timestamp_col].sort_values()
        diffs = (sorted_ts.diff().dt.total_seconds() / 60.0).dropna()
        # Count gaps significantly greater than expected frequency
        gaps = int((diffs > expected_freq_minutes * 1.5).sum())
        return gaps

    def evaluate_quality_score(self, numeric_cols: List[str], range_bounds: Dict[str, tuple] = None) -> Dict[str, Any]:
        """
        Calculates overall Data Quality Score (0 to 100).
        Deducts points for missing values, duplicates, flat-lines, out-of-range values, and gaps.
        """
        total_rows = max(len(self.df), 1)
        total_cells = total_rows * len(self.df.columns)
        
        missing_dict = self.check_missing_values()
        total_missing = sum(missing_dict.values())
        duplicates = self.check_duplicate_timestamps()
        flatlines = sum(self.check_flatline_sensors(numeric_cols).values())
        
        range_violations = 0
        if range_bounds:
            range_violations = sum(self.check_out_of_range(range_bounds).values())
            
        gaps = self.check_timestamp_gaps()
        
        # Scoring logic
        missing_pct = (total_missing / total_cells) * 100.0
        dup_pct = (duplicates / total_rows) * 100.0
        flatline_pct = (flatlines / total_rows) * 100.0
        range_pct = (range_violations / total_rows) * 100.0
        gap_penalty = min(gaps * 2.0, 20.0)
        
        raw_score = 100.0 - (missing_pct * 1.5 + dup_pct * 2.0 + flatline_pct * 1.5 + range_pct * 2.0 + gap_penalty)
        final_score = round(max(0.0, min(100.0, raw_score)), 2)
        
        quality_rating = "EXCELLENT" if final_score >= 90 else ("GOOD" if final_score >= 75 else "POOR")
        
        return {
            "data_quality_score": final_score,
            "quality_rating": quality_rating,
            "total_records": total_rows,
            "missing_values_count": total_missing,
            "duplicate_timestamps": duplicates,
            "flatline_sensor_incidents": flatlines,
            "out_of_range_count": range_violations,
            "timestamp_gaps": gaps
        }

if __name__ == "__main__":
    from src.data.generator import generate_energy_data
    df = generate_energy_data(10)
    checker = DataQualityChecker(df)
    res = checker.evaluate_quality_score(
        numeric_cols=["energy_kwh", "temperature", "hvac_load"],
        range_bounds={"energy_kwh": (0, 500), "temperature": (-10, 60)}
    )
    print("[Data Quality Test] Energy Dataset Quality Results:", res)
