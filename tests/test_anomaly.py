"""
Anomaly Detection Module Tests
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.anomaly.detector import AnomalyDetectorEngine

class TestAnomalyDetector(unittest.TestCase):
    def setUp(self):
        # Create synthetic test DataFrame
        np.random.seed(42)
        normal_data = np.random.normal(loc=50, scale=5, size=(100, 2))
        anomaly_data = np.random.normal(loc=150, scale=10, size=(5, 2))
        all_data = np.vstack([normal_data, anomaly_data])
        self.df = pd.DataFrame(all_data, columns=["feature1", "feature2"])

    def test_fit_detect_isolation_forest(self):
        engine = AnomalyDetectorEngine(method="isolation_forest", contamination=0.05)
        res_df = engine.fit_detect(self.df, ["feature1", "feature2"])
        
        self.assertIn("is_anomaly", res_df.columns)
        self.assertIn("anomaly_score", res_df.columns)
        self.assertIn("severity", res_df.columns)
        self.assertEqual(len(res_df), len(self.df))
        self.assertTrue((res_df["is_anomaly"].isin([0, 1])).all())

    def test_anomaly_explanation(self):
        engine = AnomalyDetectorEngine()
        row = pd.Series({"feature1": 150.0, "feature2": 50.0})
        means = {"feature1": 50.0, "feature2": 50.0}
        exp = engine.generate_anomaly_explanation(row, ["feature1", "feature2"], means)
        
        self.assertIsInstance(exp, str)
        self.assertIn("feature1", exp)
        self.assertIn("baseline mean", exp)

if __name__ == "__main__":
    unittest.main()
