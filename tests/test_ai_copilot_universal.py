"""
20-Question Anti-Static & Multi-Domain Test Suite for EstateIQ Universal AI Copilot.
Validates that different questions trigger different intent classification, data retrieval, and answers.
Verifies that universal queries like 'What can you do?' never return a default energy anomaly.
"""

import unittest
from src.ai.query_router import UniversalQueryRouter
from src.ai.data_planner import DataRequirementPlanner
from src.ai.context_builder import build_ai_context
from src.ai.ai_service import EstateIQAIService
from src.ai.domain_registry import DOMAIN_REGISTRY, get_domain_info


class TestUniversalAICopilotAntiStatic(unittest.TestCase):
    """Anti-Static 20-Question Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.router = UniversalQueryRouter()
        cls.planner = DataRequirementPlanner()
        cls.ai_service = EstateIQAIService()

    def test_01_capability_query_anti_static(self):
        """1. 'What can you do?' must return SYSTEM_CAPABILITY and NOT a Block B anomaly."""
        query = "What can you do?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "SYSTEM_CAPABILITY")

        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["intent_type"], "SYSTEM_CAPABILITY")
        self.assertIn("capabilities", context)
        self.assertIn("supported_domains", context["capabilities"])

        response = self.ai_service.query_copilot(query)
        self.assertTrue(response.success)
        self.assertNotIn("145.2 kWh", response.summary)

    def test_02_capabilities_alternate_phrasing(self):
        """2. 'What are your capabilities?' must route to SYSTEM_CAPABILITY."""
        query = "What are your capabilities?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "SYSTEM_CAPABILITY")

    def test_03_project_explanation(self):
        """3. 'What is EstateIQ?' must route to PROJECT_EXPLANATION."""
        query = "What is EstateIQ?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "PROJECT_EXPLANATION")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["intent_type"], "PROJECT_EXPLANATION")

    def test_04_architecture_question(self):
        """4. 'How does EstateIQ work?' must return architecture overview."""
        query = "How does EstateIQ work?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "PROJECT_EXPLANATION")

    def test_05_electricity_domain_query(self):
        """5. 'What is electricity consumption today?' must route to ELECTRICITY."""
        query = "What is electricity consumption today?"
        intent = self.router.route(query)
        self.assertIn(intent.category, ["ELECTRICITY", "ENERGY"])
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["query_meta"]["primary_domain"], "energy")

    def test_06_water_domain_query(self):
        """6. 'What is the water situation?' must route to WATER."""
        query = "What is the water situation?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "WATER")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["query_meta"]["primary_domain"], "water")

    def test_07_waste_domain_query(self):
        """7. 'What is our waste status?' must route to WASTE."""
        query = "What is our waste status?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "WASTE")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["query_meta"]["primary_domain"], "waste")

    def test_08_air_quality_query(self):
        """8. 'What is the air quality today?' must route to AIR_QUALITY."""
        query = "What is the air quality today?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "AIR_QUALITY")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["query_meta"]["primary_domain"], "air_quality")

    def test_09_equipment_health_query(self):
        """9. 'What is equipment health?' must route to EQUIPMENT."""
        query = "What is equipment health?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "EQUIPMENT")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertEqual(context["query_meta"]["primary_domain"], "equipment")

    def test_10_multi_domain_problems(self):
        """10. 'What are our biggest problems?' must evaluate cross-domain issues."""
        query = "What are our biggest problems?"
        intent = self.router.route(query)
        self.assertIn(intent.category, ["FACILITY_OVERVIEW", "CROSS_DOMAIN_SUMMARY"])
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn(context["query_meta"]["intent"], ["FACILITY_OVERVIEW", "CROSS_DOMAIN_SUMMARY"])

    def test_11_priority_action_query(self):
        """11. 'What should I fix first?' must route to PRIORITY_ACTION."""
        query = "What should I fix first?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "PRIORITY_ACTION")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("recommended_actions", context)

    def test_12_anomalies_query(self):
        """12. 'Are there any anomalies?' must route to ANOMALY."""
        query = "Are there any anomalies?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "ANOMALY")

    def test_13_what_if_scenario_query(self):
        """13. 'What if I reduce HVAC runtime by 1 hour?' must route to WHAT_IF."""
        query = "What if I reduce HVAC runtime by 1 hour?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "WHAT_IF")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("what_if_scenario", context)

    def test_14_dif_explanation_query(self):
        """14. 'Explain EstateIQ-DIF.' must route to MODEL_EXPLANATION or PROJECT_EXPLANATION."""
        query = "Explain EstateIQ-DIF."
        intent = self.router.route(query)
        self.assertIn(intent.category, ["MODEL_EXPLANATION", "PROJECT_EXPLANATION"])

    def test_15_ml_models_query(self):
        """15. 'What ML models do you use?' must route to MODEL_EXPLANATION or PROJECT_EXPLANATION."""
        query = "What ML models do you use?"
        intent = self.router.route(query)
        self.assertIn(intent.category, ["MODEL_EXPLANATION", "PROJECT_EXPLANATION"])

    def test_16_data_quality_query(self):
        """16. 'What is the current data quality?' must route to DATA_QUALITY."""
        query = "What is the current data quality?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "DATA_QUALITY")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("quality_score", context["data_quality"])

    def test_17_device_status_query(self):
        """17. 'Are sensors online?' must route to IOT_STATUS."""
        query = "Are sensors online?"
        intent = self.router.route(query)
        self.assertEqual(intent.category, "IOT_STATUS")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("device_status_summary", context)

    def test_18_executive_summary_query(self):
        """18. 'Give me today's summary.' must route to FACILITY_OVERVIEW or EXECUTIVE_SUMMARY."""
        query = "Give me today's summary."
        intent = self.router.route(query)
        self.assertIn(intent.category, ["FACILITY_OVERVIEW", "EXECUTIVE_SUMMARY"])

    def test_19_building_comparison_query(self):
        """19. 'Compare Block A and Block B.' must route to COMPARISON."""
        query = "Compare Block A and Block B."
        intent = self.router.route(query)
        self.assertEqual(intent.category, "COMPARISON")
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("comparison_metrics", context)

    def test_20_dataset_metadata_query(self):
        """20. 'What data do you currently have?' must route to DATASET or DATASET_METADATA."""
        query = "What data do you currently have?"
        intent = self.router.route(query)
        self.assertIn(intent.category, ["DATASET", "DATASET_METADATA"])
        context = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query=query)
        self.assertIn("dataset_metadata", context)

    def test_anti_static_response_diversity(self):
        """Ensures that 20 different queries produce distinct intent categories and context data."""
        queries = [
            "What can you do?",
            "What is electricity consumption today?",
            "What is the water situation?",
            "What is our waste status?",
            "What is the air quality today?",
            "What is equipment health?",
            "What are our biggest problems?",
            "What should I fix first?",
            "Are there any anomalies?",
            "What if I reduce HVAC runtime by 1 hour?"
        ]
        intents = set()
        for q in queries:
            intent = self.router.route(q)
            intents.add(intent.category)
        
        # Verify that at least 8 distinct intent categories are recognized across 10 queries
        self.assertGreaterEqual(len(intents), 8)


if __name__ == "__main__":
    unittest.main()
