"""Focused tests for the history-based baseline and interval impact fixes."""

import unittest
import tempfile
from pathlib import Path
import pandas as pd

from src.intelligence.seasonal_baseline import SeasonalBaselineModel
from src.intelligence.context_filter import EstateIQContextFilter
from src.intelligence.types import EventData
from src.intelligence.config import DIFConfig
from src.intelligence.business_impact import IntelligenceBusinessImpactEngine


class TestSeasonalBaseline(unittest.TestCase):
    def test_fit_uses_time_and_building_but_ignores_label_columns(self):
        ts = pd.date_range("2026-01-05", periods=14 * 96, freq="15min", tz="Asia/Kolkata")
        frame = pd.DataFrame({
            "timestamp": ts,
            "building_id": "B1",
            "electricity_kwh": 25.0,
            "anomaly_flag": 0,
        })
        frame.loc[0, "anomaly_flag"] = 1
        model = SeasonalBaselineModel(min_observations=2).fit(frame)
        # Monday 00:00 has two training observations; evaluation labels had no effect.
        estimate = model.predict("B1", "2026-01-19T00:00:00+05:30")
        self.assertIsNotNone(estimate)
        self.assertEqual(estimate.expected_kwh, 25.0)
        self.assertEqual(estimate.observations, 2)

    def test_context_uses_fitted_baseline_and_two_sided_residual(self):
        ts = pd.date_range("2026-01-05", periods=14 * 96, freq="15min", tz="Asia/Kolkata")
        frame = pd.DataFrame({"timestamp": ts, "building_id": "B1", "energy_kwh": 20.0})
        model = SeasonalBaselineModel(min_observations=2).fit(frame)
        event = EventData("e1", "f1", "B1", "2026-01-19T14:00:00+05:30", 5.0,
                          14, 0, 1, 25.0, interval_hours=0.25)
        result = EstateIQContextFilter(DIFConfig()).evaluate(event, model)
        self.assertEqual(result.expected_kwh, 20.0)
        self.assertEqual(result.baseline_source, "SEASONAL_MEDIAN_MAD")
        self.assertLess(result.residual_kwh, 0)
        self.assertFalse(result.early_exit)

    def test_interval_energy_cost_extrapolates_rate_not_interval_as_hour(self):
        impact = IntelligenceBusinessImpactEngine(grid_tariff_inr_kwh=10.0,
                                                   grid_emission_factor_kg_kwh=1.0)
        result = impact.calculate_surge_impact(12.0, 10.0, duration_hours=0.25)
        self.assertEqual(result["residual_surge_kwh"], 2.0)
        self.assertEqual(result["hourly_cost_impact_inr"], 80.0)
        self.assertEqual(result["interval_hours"], 0.25)

    def test_json_artifact_round_trip(self):
        ts = pd.date_range("2026-01-05", periods=14 * 96, freq="15min", tz="Asia/Kolkata")
        frame = pd.DataFrame({"timestamp": ts, "building_id": "B1", "energy_kwh": 20.0})
        fitted = SeasonalBaselineModel(min_observations=2).fit(frame)
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / "baseline.json"
            fitted.save(artifact)
            loaded = SeasonalBaselineModel.load(artifact)
        self.assertEqual(loaded.training_rows, fitted.training_rows)
        self.assertEqual(loaded.predict("B1", "2026-01-19T14:00:00+05:30"),
                         fitted.predict("B1", "2026-01-19T14:00:00+05:30"))


if __name__ == "__main__":
    unittest.main()
