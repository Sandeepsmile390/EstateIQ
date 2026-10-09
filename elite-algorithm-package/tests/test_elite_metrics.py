"""
Unit tests for Mathematical Metric Formulas (elite-algorithm-package/tests/test_metrics.py).
"""

import unittest
import numpy as np
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = PACKAGE_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from elite_algo.metrics import ForecastingMetrics, BaselineModels, ClassificationMetrics, DecisionLayerMetrics

class TestMetricsFormulas(unittest.TestCase):

    def test_forecasting_metrics_exact_values(self):
        y_true = np.array([10.0, 20.0, 30.0, 40.0])
        y_pred = np.array([12.0, 18.0, 33.0, 37.0])

        res = ForecastingMetrics.calculate_all(y_true, y_pred)
        # MAE: (|2| + |-2| + |3| + |-3|)/4 = 10/4 = 2.5
        self.assertEqual(res["mae"], 2.5)
        self.assertGreater(res["r2"], 0.8)

    def test_naive_persistence(self):
        train = np.array([10.0, 15.0, 20.0])
        test = np.array([25.0, 30.0, 35.0])

        preds = BaselineModels.naive_persistence(train, test)
        self.assertEqual(preds[0], 20.0)
        self.assertEqual(preds[1], 25.0)
        self.assertEqual(preds[2], 30.0)

    def test_classification_metrics(self):
        y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0])
        y_pred = np.array([1, 0, 1, 0, 0, 0, 1, 0])

        res = ClassificationMetrics.calculate_all(y_true, y_pred)
        self.assertEqual(res["status"], "EVALUATED")
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["confusion_matrix"]["tp"], 3)
        self.assertEqual(res["confusion_matrix"]["fn"], 1)

    def test_decision_layer_metrics(self):
        records = [
            {"model_agreement_pct": 90.0, "suppressed_by_safety_gate": False, "priority": "P1_CRITICAL", "hourly_cost_inr": 450.0, "confidence_percent": 95.0},
            {"model_agreement_pct": 80.0, "suppressed_by_safety_gate": True, "priority": "P3_ROUTINE", "hourly_cost_inr": 0.0, "confidence_percent": 85.0}
        ]
        res = DecisionLayerMetrics.evaluate_decision_layer(records)
        self.assertEqual(res["status"], "EVALUATED")
        self.assertEqual(res["mean_model_agreement_pct"], 85.0)
        self.assertEqual(res["false_alert_suppression_rate_pct"], 50.0)

if __name__ == "__main__":
    unittest.main()
