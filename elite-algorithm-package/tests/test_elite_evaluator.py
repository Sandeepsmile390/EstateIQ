"""
Unit tests for PackageEvaluator (elite-algorithm-package/tests/test_evaluator.py).
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

from elite_algo.evaluator import PackageEvaluator

class TestPackageEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = PackageEvaluator()

    def test_evaluate_all(self):
        res = self.evaluator.evaluate_all()
        self.assertIn("energy_results", res)
        self.assertIn("water_results", res)
        self.assertIn("anomaly_results", res)
        self.assertIn("decision_results", res)
        self.assertIn("summary_df", res)

        summary_df = res["summary_df"]
        self.assertFalse(summary_df.empty)
        self.assertIn("Metric Name", summary_df.columns)
        self.assertIn("Measured Value", summary_df.columns)

if __name__ == "__main__":
    unittest.main()
