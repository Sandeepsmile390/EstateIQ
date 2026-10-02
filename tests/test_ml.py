"""
Machine Learning Model Loading and Inference Tests
"""

import unittest
import os
import joblib
import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

class TestMLModels(unittest.TestCase):
    def setUp(self):
        self.models_dir = BASE_DIR / "models"
        self.assertTrue(self.models_dir.exists(), "Models directory must exist")

    def test_registered_model_files(self):
        model_files = [f for f in os.listdir(self.models_dir) if f.endswith(".joblib")]
        self.assertGreater(len(model_files), 0, "Saved joblib model files must exist")

    def test_energy_model_load_and_predict(self):
        model_path = self.models_dir / "energy_kwh_prediction_model.joblib"
        meta_path = self.models_dir / "energy_kwh_prediction_metadata.joblib"
        
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_input = np.ones((1, len(features)))
            pred = model.predict(dummy_input)
            self.assertEqual(len(pred), 1)

    def test_waste_model_load_and_predict(self):
        model_path = self.models_dir / "waste_overflow_2hr_model.joblib"
        meta_path = self.models_dir / "waste_overflow_2hr_metadata.joblib"
        
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_input = np.ones((1, len(features)))
            pred = model.predict(dummy_input)
            self.assertEqual(len(pred), 1)

    def test_equipment_risk_model(self):
        model_path = self.models_dir / "equipment_maintenance_risk_model.joblib"
        meta_path = self.models_dir / "equipment_maintenance_risk_metadata.joblib"
        
        if model_path.exists() and meta_path.exists():
            model = joblib.load(model_path)
            meta = joblib.load(meta_path)
            features = meta.get("feature_names", meta.get("features", []))
            self.assertGreater(len(features), 0)
            dummy_input = np.ones((1, len(features)))
            pred = model.predict(dummy_input)
            self.assertEqual(len(pred), 1)

if __name__ == "__main__":
    unittest.main()
