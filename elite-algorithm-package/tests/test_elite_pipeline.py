"""
Unit tests for EliteAlgorithmPipeline (elite-algorithm-package/tests/test_pipeline.py).
"""

import unittest
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from elite_algo.pipeline import EliteAlgorithmPipeline

class TestEliteAlgorithmPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = EliteAlgorithmPipeline()

    def test_pipeline_execution(self):
        res = self.pipeline.process_telemetry_event(
            facility_id="FAC_GEC_CAMPUS",
            building_id="Block B Hostel",
            actual_kwh=165.4,
            occupancy=180,
            temperature_c=34.5,
            hvac_load_kw=72.0
        )
        self.assertIn("event_id", res)
        self.assertIn("telemetry", res)
        self.assertIn("contextual_baseline", res)
        self.assertIn("anomaly", res)
        self.assertIn("confidence", res)
        self.assertIn("business_impact", res)
        self.assertIn("decision_priority", res)
        self.assertIn("shap_attribution", res)

        self.assertEqual(res["telemetry"]["actual_kwh"], 165.4)
        self.assertGreater(res["contextual_baseline"]["expected_kwh"], 0)

if __name__ == "__main__":
    unittest.main()
