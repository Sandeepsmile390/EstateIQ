"""
What-If Scenario Simulation Tests
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.scenarios.whatif import WhatIfScenarioEngine

class DummyModel:
    def predict(self, X):
        # Predict sum of row values
        return np.sum(X, axis=1)

class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.dummy_model = DummyModel()
        self.features = ["hvac_load", "lighting_load"]
        self.engine = WhatIfScenarioEngine(self.dummy_model, self.features)
        self.df = pd.DataFrame([{"hvac_load": 100.0, "lighting_load": 50.0}])

    def test_hvac_reduction_scenario(self):
        # Reduce HVAC by 20%
        mods = {"hvac_load": 0.80}
        res = self.engine.run_scenario(self.df, mods)
        
        self.assertEqual(res["current_scenario_prediction"], 150.0)
        self.assertEqual(res["simulated_scenario_prediction"], 130.0)
        self.assertEqual(res["absolute_difference"], -20.0)
        self.assertIn("disclaimer", res)

if __name__ == "__main__":
    unittest.main()
