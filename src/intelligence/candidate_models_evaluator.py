"""Candidate Machine Learning Models Evaluator (src/intelligence/candidate_models_evaluator.py).

Provides an optional parallel comparison mode evaluating trained candidate models
(Random Forest, Isolation Forest) alongside EstateIQ-DIF without altering the primary
DIF decision path, alerting behavior, or database schemas.

Guarantees:
- Primary alert decision is 100% driven by EstateIQ-DIF.
- Candidate models run in parallel observation mode only.
- Strict isolation between raw model score and binary alert decision.
- Explicit handling of invalid, missing, stale, or corrupt telemetry.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np

from src.benchmarks.model_training_bench import (
    FEATURE_COLUMNS,
    extract_model_features,
)
from src.intelligence.dif_engine import EstateIQDIF
from src.intelligence.sensor_health import SensorHealthEngine, SensorHealthResult
from src.intelligence.types import DecisionResult, EventData

logger = logging.getLogger("CandidateModelsEvaluator")


@dataclass
class CandidateModelPrediction:
    """Holds individual candidate model output distinguishing score from alert flag."""
    model_name: str
    model_type: str  # "Supervised (Tree Ensemble)", "Unsupervised (Partitioning)"
    raw_score: float
    calibrated_threshold: float
    is_anomaly: bool
    confidence: float
    features_evaluated: int


@dataclass
class MultiModelComparisonResult:
    """Encapsulates the primary EstateIQ-DIF result along with candidate model comparisons."""
    primary_decision: DecisionResult
    primary_algorithm: str
    comparison_mode_active: bool
    sensor_health: SensorHealthResult
    candidate_predictions: Dict[str, CandidateModelPrediction]
    model_consensus_agreement_pct: float


class CandidateModelsEvaluator:
    """Manages optional parallel inference for serialized ML models alongside EstateIQ-DIF."""

    def __init__(
        self,
        dif_engine: Optional[EstateIQDIF] = None,
        models_dir: Optional[Path] = None,
        enable_comparison: bool = True,
    ):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.models_dir = models_dir or (
            self.root_dir / "output/presentation/synthetic_model_training/models"
        )
        self.dif_engine = dif_engine or EstateIQDIF()
        self.sensor_health_engine = SensorHealthEngine()
        self.enable_comparison = enable_comparison

        self.rf_model = None
        self.iso_model = None
        self.scaler = None
        self.tau_rf = 0.3200
        self.tau_iso = 0.6118

        if self.enable_comparison:
            self._load_serialized_models()

    def _load_serialized_models(self) -> None:
        """Loads serialized Random Forest, Isolation Forest, and Scaler from disk."""
        rf_path = self.models_dir / "random_forest_model.joblib"
        iso_path = self.models_dir / "isolation_forest_model.joblib"
        scaler_path = self.models_dir / "scaler.joblib"

        if rf_path.exists() and iso_path.exists() and scaler_path.exists():
            try:
                self.rf_model = joblib.load(rf_path)
                self.iso_model = joblib.load(iso_path)
                self.scaler = joblib.load(scaler_path)
                logger.info("Successfully loaded candidate ML models from %s", self.models_dir)
            except Exception as e:
                logger.warning("Failed to load candidate models (%s); comparison mode disabled", e)
                self.enable_comparison = False
        else:
            logger.warning("Candidate model artifacts not found at %s; comparison mode disabled", self.models_dir)
            self.enable_comparison = False

    def evaluate(self, event: EventData) -> MultiModelComparisonResult:
        """Processes event through primary DIF engine and optional candidate models."""
        bld = event.building_id or "default"
        kwh = float(event.actual_kwh) if event.actual_kwh is not None else -1.0

        # 1. Hardware Sensor Health Evaluation
        sensor_res = self.sensor_health_engine.evaluate(bld, event.timestamp, kwh)

        # 2. Primary Decision Path: EstateIQ-DIF (Unchanged)
        dif_result = self.dif_engine.analyze(event)

        candidate_preds: Dict[str, CandidateModelPrediction] = {}
        agreement_count = 0
        total_evaluators = 1  # DIF is always 1

        is_dif_anom = (dif_result.anomaly.anomaly_score >= self.dif_engine.config.anomaly_score_threshold)
        if is_dif_anom:
            agreement_count += 1

        # 3. Optional Candidate Models (Observation Mode Only)
        if self.enable_comparison and self.rf_model and self.scaler:
            try:
                # Build mock single-row DataFrame for feature extraction
                import pandas as pd
                df_single = pd.DataFrame([{
                    "timestamp": event.timestamp,
                    "building_id": bld,
                    "electricity_kwh": kwh,
                    "hvac_kwh": float(getattr(event, "hvac_load", 0.0) or 0.0),
                    "lighting_kwh": float(getattr(event, "lighting_kwh", 0.0) or 0.0),
                    "equipment_kwh": float(getattr(event, "equipment_kwh", 0.0) or 0.0),
                    "other_kwh": float(getattr(event, "other_kwh", 0.0) or 0.0),
                    "power_factor": float(event.extra_features.get("power_factor", 0.95) if event.extra_features else 0.95),
                    "temperature_c": float(getattr(event, "temperature", 25.0) or 25.0),
                    "occupancy_count": int(getattr(event, "occupancy", 0) or 0),
                }])

                feat = extract_model_features(df_single)
                feat_scaled = self.scaler.transform(feat)

                # Random Forest Prediction
                rf_prob = float(self.rf_model.predict_proba(feat_scaled)[0, 1])
                rf_flag = bool(rf_prob >= self.tau_rf)
                candidate_preds["Random Forest"] = CandidateModelPrediction(
                    model_name="Random Forest Classifier",
                    model_type="Supervised (Tree Ensemble)",
                    raw_score=round(rf_prob, 4),
                    calibrated_threshold=self.tau_rf,
                    is_anomaly=rf_flag,
                    confidence=round(abs(rf_prob - 0.5) * 2.0, 2),
                    features_evaluated=len(FEATURE_COLUMNS),
                )
                total_evaluators += 1
                if rf_flag == is_dif_anom:
                    agreement_count += 1

                # Isolation Forest Prediction
                if self.iso_model:
                    iso_score = float(-self.iso_model.score_samples(feat_scaled)[0])
                    iso_flag = bool(iso_score >= self.tau_iso)
                    candidate_preds["Isolation Forest"] = CandidateModelPrediction(
                        model_name="Isolation Forest (Contextual)",
                        model_type="Unsupervised (Partitioning)",
                        raw_score=round(iso_score, 4),
                        calibrated_threshold=self.tau_iso,
                        is_anomaly=iso_flag,
                        confidence=round(min(1.0, max(0.0, (iso_score - 0.5) / 0.5)), 2),
                        features_evaluated=len(FEATURE_COLUMNS),
                    )
                    total_evaluators += 1
                    if iso_flag == is_dif_anom:
                        agreement_count += 1

            except Exception as e:
                logger.warning("Candidate model inference error: %s", e)

        consensus_pct = round((agreement_count / max(total_evaluators, 1)) * 100.0, 1)

        return MultiModelComparisonResult(
            primary_decision=dif_result,
            primary_algorithm="EstateIQ-DIF V3",
            comparison_mode_active=self.enable_comparison,
            sensor_health=sensor_res,
            candidate_predictions=candidate_preds,
            model_consensus_agreement_pct=consensus_pct,
        )

