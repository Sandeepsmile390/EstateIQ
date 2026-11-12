"""Dataset discovery, schema validation, and provenance auditing.

Finds and verifies the repository's synthetic energy dataset, computes reproducible
checksum fingerprints, and audits available ground-truth labels and context fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


@dataclass
class DatasetMetadata:
    """Auditable metadata and integrity summary for an evaluated dataset."""
    file_path: str
    sha256_fingerprint: str
    total_rows: int
    date_start: str
    date_end: str
    buildings: List[str]
    sampling_interval_minutes: float
    missing_energy_rows: int
    missing_energy_pct: float
    has_ground_truth_labels: bool
    anomaly_counts: Dict[str, int] = field(default_factory=dict)
    anomaly_types: Dict[str, int] = field(default_factory=dict)
    anomaly_prevalence_pct: float = 0.0
    provenance_badge: str = "[SYNTHETIC DATA — PHYSICS CONSTRAINED]"
    provenance_notes: str = (
        "Dataset generated with physics-informed facility baseline rules and "
        "explicit synthetic anomaly injection episodes. Not measured production telemetry."
    )
    available_columns: List[str] = field(default_factory=list)


class DatasetLoader:
    """Discovers, validates, and prepares facility energy datasets for benchmarking."""

    DEFAULT_CANDIDATE_PATHS = [
        Path("facility_dataset/data/raw/energy_readings.csv"),
        Path("facility_dataset/data/ml/energy_forecasting.csv"),
        Path("data/synthetic/energy.csv"),
    ]

    REQUIRED_ENERGY_COLS = ("electricity_kwh", "energy_kwh")

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def discover_default_dataset_path(self) -> Optional[Path]:
        """Locates the primary synthetic energy dataset in the repository."""
        for rel_path in self.DEFAULT_CANDIDATE_PATHS:
            full_path = (self.project_root / rel_path).resolve()
            if full_path.is_file():
                return full_path
        return None

    @staticmethod
    def compute_sha256(file_path_or_bytes: Union[Path, str, bytes, io.BytesIO]) -> str:
        """Computes a SHA-256 hex digest for dataset reproducibility."""
        hasher = hashlib.sha256()
        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        elif isinstance(file_path_or_bytes, bytes):
            hasher.update(file_path_or_bytes)
        elif hasattr(file_path_or_bytes, "read"):
            pos = file_path_or_bytes.tell() if hasattr(file_path_or_bytes, "tell") else None
            while chunk := file_path_or_bytes.read(65536):
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                hasher.update(chunk)
            if pos is not None:
                file_path_or_bytes.seek(pos)
        return hasher.hexdigest()

    def load_dataset(
        self,
        source: Optional[Union[Path, str, io.BytesIO, bytes]] = None,
        max_rows: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, DatasetMetadata]:
        """Loads and validates a facility energy dataset.

        Args:
            source: Path to CSV or file-like object. If None, discovers the default repo dataset.
            max_rows: Optional limit on rows to load for fast preview.

        Returns:
            Tuple of (DataFrame, DatasetMetadata).

        Raises:
            FileNotFoundError: If no candidate dataset can be found.
            ValueError: If required columns are missing or unparseable.
        """
        source_label = "uploaded_file.csv"
        raw_bytes: Optional[bytes] = None

        if source is None:
            disc = self.discover_default_dataset_path()
            if disc is None:
                raise FileNotFoundError(
                    "Could not locate the primary repository dataset. Looked for: "
                    + ", ".join(str(p) for p in self.DEFAULT_CANDIDATE_PATHS)
                )
            target = disc
            source_label = str(disc)
            sha256 = self.compute_sha256(disc)
            df = pd.read_csv(disc, nrows=max_rows)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"Dataset file not found at {path}")
            target = path
            source_label = str(path)
            sha256 = self.compute_sha256(path)
            df = pd.read_csv(path, nrows=max_rows)
        else:
            # File-like object (e.g., Streamlit UploadedFile)
            if hasattr(source, "name"):
                source_label = getattr(source, "name", "uploaded_file.csv")
            sha256 = self.compute_sha256(source)
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, nrows=max_rows)

        # 1. Validate Schema
        cols = df.columns.tolist()
        if "timestamp" not in cols:
            raise ValueError("Invalid dataset schema: missing required 'timestamp' column.")

        energy_col = next((c for c in self.REQUIRED_ENERGY_COLS if c in cols), None)
        if not energy_col:
            raise ValueError(
                f"Invalid dataset schema: missing energy consumption column. "
                f"Expected one of: {self.REQUIRED_ENERGY_COLS}. Found: {cols}"
            )

        if "building_id" not in cols:
            # Fallback to single facility or default tag
            df["building_id"] = "BLD_DEFAULT"

        # Standardize column names if needed
        if energy_col != "electricity_kwh" and "electricity_kwh" not in cols:
            df["electricity_kwh"] = pd.to_numeric(df[energy_col], errors="coerce")

        # Convert timestamps
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values(["building_id", "timestamp"]).reset_index(drop=True)

        if df.empty:
            raise ValueError("Dataset has no valid timestamps after parsing.")

        # 2. Inquire ground truth labels
        has_gt = "anomaly_flag" in cols
        anomaly_counts: Dict[str, int] = {}
        anomaly_types: Dict[str, int] = {}
        anom_pct = 0.0

        if has_gt:
            flags = pd.to_numeric(df["anomaly_flag"], errors="coerce").fillna(0).astype(int)
            positives = int(np.sum(flags == 1))
            negatives = int(np.sum(flags == 0))
            anomaly_counts = {"normal": negatives, "anomaly": positives}
            anom_pct = round((positives / len(df)) * 100.0, 4)
            if "anomaly_type" in cols:
                anomaly_types = df["anomaly_type"].value_counts().to_dict()

        # 3. Compute sampling interval
        sample_intervals: List[float] = []
        for _, b_group in df.groupby("building_id"):
            if len(b_group) > 1:
                diffs = b_group["timestamp"].diff().dropna().dt.total_seconds() / 60.0
                median_diff = float(diffs.median())
                if median_diff > 0:
                    sample_intervals.append(median_diff)
        sampling_interval = float(np.median(sample_intervals)) if sample_intervals else 15.0

        # Missing energy count
        missing_energy = int(df["electricity_kwh"].isna().sum())
        missing_pct = round((missing_energy / len(df)) * 100.0, 2)

        meta = DatasetMetadata(
            file_path=source_label,
            sha256_fingerprint=sha256,
            total_rows=len(df),
            date_start=df["timestamp"].min().isoformat(),
            date_end=df["timestamp"].max().isoformat(),
            buildings=df["building_id"].unique().tolist(),
            sampling_interval_minutes=sampling_interval,
            missing_energy_rows=missing_energy,
            missing_energy_pct=missing_pct,
            has_ground_truth_labels=has_gt,
            anomaly_counts=anomaly_counts,
            anomaly_types=anomaly_types,
            anomaly_prevalence_pct=anom_pct,
            available_columns=cols,
        )

        return df, meta
