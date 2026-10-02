"""
Forecasting Module Tests
"""

import unittest
from pathlib import Path
import sys
import joblib
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

class TestForecasting(unittest.TestCase):
    def setUp(self):
        self.models_dir = BASE_DIR / "models"

    def test_water_forecasting(self):
        model_path = self.models_dir / "water_usage_forecasting_model.joblib"
        meta_path = self.models_dir / "water_usage_forecasting_metadata.joblib"
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_x = np.ones((1, len(features)))
            pred = model.predict(dummy_x)
            self.assertGreaterEqual(pred[0], 0, "Water forecast prediction must be >= 0")

    def test_emissions_forecasting(self):
        model_path = self.models_dir / "emissions_forecasting_model.joblib"
        meta_path = self.models_dir / "emissions_forecasting_metadata.joblib"
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_x = np.ones((1, len(features)))
            pred = model.predict(dummy_x)
            self.assertGreaterEqual(pred[0], 0, "Emissions forecast prediction must be >= 0")

    def test_parking_forecasting(self):
        model_path = self.models_dir / "parking_occupancy_forecasting_model.joblib"
        meta_path = self.models_dir / "parking_occupancy_forecasting_metadata.joblib"
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_x = np.ones((1, len(features)))
            pred = model.predict(dummy_x)
            self.assertIsInstance(pred[0], (float, np.floating, int, np.integer))

if __name__ == "__main__":
    unittest.main()
