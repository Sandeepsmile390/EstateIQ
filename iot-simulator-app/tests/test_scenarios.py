import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulator.scenario_engine import ScenarioEngine

class TestScenarioEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ScenarioEngine()

    def test_list_scenarios(self):
        scenarios = self.engine.list_scenarios()
        self.assertGreaterEqual(len(scenarios), 14)
        names = [s["name"] for s in scenarios]
        self.assertIn("Normal Campus Operation", names)
        self.assertIn("High HVAC Consumption", names)
        self.assertIn("Gradual Water Leakage", names)

    def test_apply_hvac_scenario(self):
        device_dict = {"device_id": "HVAC-001", "profile": "HVAC Monitor"}
        raw_sample = {"readings": {"hvac_load": 45.0, "active_power": 100.0}, "units": {}, "quality": "good"}

        modified = self.engine.apply_scenario("High HVAC Consumption", device_dict, raw_sample)
        self.assertGreater(modified["readings"]["hvac_load"], 45.0)

    def test_apply_water_leak_scenario(self):
        device_dict = {"device_id": "WATER-001", "profile": "Water Flow Meter"}
        raw_sample = {"readings": {"water_flow": 50.0}, "units": {}, "quality": "good"}

        modified = self.engine.apply_scenario("Gradual Water Leakage", device_dict, raw_sample)
        self.assertGreater(modified["readings"]["water_flow"], 50.0)

if __name__ == "__main__":
    unittest.main()
