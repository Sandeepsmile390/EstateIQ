"""
Dataset A/B Synchronization & Full Data-Driven Reactivity Test Suite.
Validates that switching between Dataset A (Baseline) and Dataset B (High Surge) dynamically updates
all KPIs, telemetry readings, backend services, recommendations, AI Insights, and Copilot query responses.
"""

import unittest
from src.data.dataset_manager import GLOBAL_DATASET_MANAGER
from src.ai.backend_services import EstateIQBackendServices
from src.ai.insight_service import GLOBAL_AI_INSIGHT_SERVICE
from src.ai.ai_service import EstateIQAIService
from src.ai.context_builder import build_ai_context
from src.ai.exceptions import GroqRateLimitError

class TestDatasetSynchronization(unittest.TestCase):
    """End-to-End Dataset Synchronization and Dynamic UI Reactivity Test."""

    @classmethod
    def setUpClass(cls):
        cls.backend = EstateIQBackendServices()
        cls.ai_insight_svc = GLOBAL_AI_INSIGHT_SERVICE
        cls.copilot_svc = EstateIQAIService()

    def setUp(self):
        # Reset to Dataset A before each test
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_a")

    def test_01_dataset_switching_metadata(self):
        """1. Verify metadata updates when switching from Dataset A to Dataset B."""
        info_a = GLOBAL_DATASET_MANAGER.get_dataset_info()
        self.assertEqual(info_a["dataset_id"], "estateiq-dataset-a-standard")
        self.assertEqual(info_a["multiplier"], 1.0)

        switch_res = GLOBAL_DATASET_MANAGER.switch_dataset("dataset_b")
        self.assertTrue(switch_res["cache_invalidated"])

        info_b = GLOBAL_DATASET_MANAGER.get_dataset_info()
        self.assertEqual(info_b["dataset_id"], "estateiq-dataset-b-high-surge")
        self.assertEqual(info_b["multiplier"], 1.85)

    def test_02_backend_services_reactivity(self):
        """2. Verify backend telemetry metrics scale dynamically when dataset changes."""
        # Dataset A baseline values
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_a")
        e_a = self.backend.get_energy_summary("Block B Hostel")
        w_a = self.backend.get_water_summary()

        # Switch to Dataset B
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_b")
        e_b = self.backend.get_energy_summary("Block B Hostel")
        w_b = self.backend.get_water_summary()

        # Asserts that Dataset B metrics are materially different from Dataset A
        self.assertNotEqual(e_a["electricity_kwh"], e_b["electricity_kwh"])
        self.assertGreater(e_b["electricity_kwh"], e_a["electricity_kwh"])
        self.assertNotEqual(w_a["consumption_liters"], w_b["consumption_liters"])
        self.assertGreater(w_b["consumption_liters"], w_a["consumption_liters"])

    def test_03_ai_insight_service_reactivity(self):
        """3. Verify AI Insights update dynamically when dataset changes."""
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_a")
        insight_a = self.ai_insight_svc.get_domain_insight("energy", "Block B Hostel")

        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_b")
        insight_b = self.ai_insight_svc.get_domain_insight("energy", "Block B Hostel")

        self.assertNotEqual(insight_a.what_happened, insight_b.what_happened)
        self.assertIn("1.85", str(GLOBAL_DATASET_MANAGER.active_dataset.multiplier))

    def test_04_copilot_context_and_query_reactivity(self):
        """4. Verify AI Copilot evidence packet and query response change with dataset."""
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_a")
        ctx_a = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query="What is the current electricity situation?")

        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_b")
        ctx_b = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query="What is the current electricity situation?")

        self.assertNotEqual(ctx_a["query_meta"]["data_source"], ctx_b["query_meta"]["data_source"])
        self.assertNotEqual(ctx_a["telemetry_observed"]["actual_kwh"], ctx_b["telemetry_observed"]["actual_kwh"])

    def test_05_cache_invalidation_on_switch(self):
        """5. Verify global cache is invalidated when dataset switches."""
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_a")
        # Populate cache manually or via query
        self.copilot_svc._cache["test_cache_key"] = "mock_response"
        self.assertGreater(len(self.copilot_svc._cache), 0)

        # Switch dataset should clear cache
        GLOBAL_DATASET_MANAGER.switch_dataset("dataset_b")
        self.assertEqual(len(self.copilot_svc._cache), 0)


if __name__ == "__main__":
    unittest.main()
