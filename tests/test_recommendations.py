"""
Recommendation Engine Tests
"""

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.recommendations.genai_engine import GenAIExplanationEngine

class TestRecommendations(unittest.TestCase):
    def setUp(self):
        self.engine = GenAIExplanationEngine()

    def test_energy_recommendation_structure(self):
        payload = {
            "issue": "energy_anomaly",
            "building": "Block B Hostel",
            "actual": 120.0,
            "expected": 85.0,
            "deviation_percent": 41.1,
            "important_features": ["occupancy", "temperature"]
        }
        res = self.engine.generate_recommendation(payload)
        
        self.assertIn("title", res)
        self.assertEqual(res["4_severity"], "HIGH")
        self.assertIn("1_what_happened", res)
        self.assertIn("2_what_is_predicted", res)
        self.assertIn("3_why_was_it_flagged", res)
        self.assertIn("5_recommended_action", res)
        self.assertIn("6_assumptions", res)
        self.assertIn("7_limitations", res)

    def test_water_recommendation(self):
        payload = {
            "issue": "water_leak",
            "building": "Admin Block",
            "actual": 50.0,
            "expected": 10.0,
            "deviation_percent": 400.0,
            "important_features": ["flow_rate"]
        }
        res = self.engine.generate_recommendation(payload)
        self.assertEqual(res["4_severity"], "HIGH")
        self.assertIn("supply line valves", res["5_recommended_action"])

if __name__ == "__main__":
    unittest.main()
