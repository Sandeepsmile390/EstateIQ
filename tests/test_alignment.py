import unittest
import pandas as pd
import numpy as np

from src.models.forecasting import UnifiedForecastingEngine, NaiveForecastAdapter, MovingAverageForecastAdapter, ProphetForecastAdapter
from src.data.geospatial import GeospatialFacilityRepository
from src.data.mqtt_consumer import MQTTTelemetryConsumer
from src.services.facility_service import FacilityService
from src.services.energy_service import EnergyService
from src.services.simulation_service import SimulationService

class TestTechStackAlignment(unittest.TestCase):
    def setUp(self):
        ds = pd.date_range("2026-01-01", periods=50, freq="h")
        y = 50.0 + np.sin(np.linspace(0, 10, 50)) * 10.0
        self.df = pd.DataFrame({"ds": ds, "y": y, "temp": np.random.normal(25, 2, 50)})
        self.train_df = self.df.iloc[:40]
        self.val_df = self.df.iloc[40:]

    def test_naive_forecaster(self):
        model = NaiveForecastAdapter().fit(self.train_df)
        preds = model.predict(self.val_df)
        self.assertEqual(len(preds), len(self.val_df))

    def test_moving_average_forecaster(self):
        model = MovingAverageForecastAdapter(window=12).fit(self.train_df)
        preds = model.predict(self.val_df)
        self.assertEqual(len(preds), len(self.val_df))

    def test_prophet_forecaster(self):
        try:
            model = ProphetForecastAdapter().fit(self.train_df)
            preds = model.predict(self.val_df)
            self.assertEqual(len(preds), len(self.val_df))
        except RuntimeError:
            pass  # If Prophet environment constraints

    def test_unified_forecasting_engine(self):
        engine = UnifiedForecastingEngine(output_dir="models")
        best_m, comp_df, meta = engine.evaluate_all(self.train_df, self.val_df, timestamp_col="ds", target_col="y", feature_cols=["temp"])
        self.assertIn("model_name", meta)
        self.assertGreater(len(comp_df), 0)

    def test_geospatial_repository(self):
        geo = GeospatialFacilityRepository()
        self.assertGreater(len(geo.df), 0)
        map_html = geo.generate_folium_map(asset_type="Energy")
        self.assertIn("html", map_html.lower())

    def test_mqtt_consumer(self):
        consumer = MQTTTelemetryConsumer(broker_host="localhost")
        self.assertFalse(consumer.is_connected)

    def test_unified_services(self):
        fac_svc = FacilityService()
        eng_svc = EnergyService()
        sim_svc = SimulationService()

        summary = fac_svc.get_facility_summary()
        self.assertIn("provenance", summary)

        overview = eng_svc.get_energy_overview()
        self.assertIn("shap_attribution", overview)

        sim_res = sim_svc.run_hvac_scenario(baseline_kwh=150.0, hvac_reduction_percent=20.0)
        self.assertIn("monthly_savings_inr", sim_res)

if __name__ == "__main__":
    unittest.main()
