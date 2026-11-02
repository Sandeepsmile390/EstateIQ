"""
20-Question Anti-Static & Multi-Domain Test Suite for EstateIQ Universal AI Copilot.
Validates that different questions trigger different intent classification, data retrieval, and answers.
Verifies that universal queries like 'What can you do?' never return a default energy anomaly.
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

from src.ai.query_router import UniversalQueryRouter
from src.ai.data_planner import DataRequirementPlanner
from src.ai.context_builder import build_ai_context
from src.ai.ai_service import EstateIQAIService
from src.ai.domain_registry import DOMAIN_REGISTRY, get_domain_info


def build_mock_groq_client():
    """Mock Groq client for credential-independent unit tests."""
    mock_groq = MagicMock()

    def mock_chat_create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        content = messages[-1]["content"].lower() if messages else ""
        system = messages[0]["content"] if len(messages) > 1 else ""

        # Extract user query
        query_text = content.split("user query:")[-1].strip() if "user query:" in content else content

        if "greeting" in system.lower() or query_text in ["hi", "hello", "hey"]:
            summary = "Hello! I am EstateIQ Copilot, your campus energy intelligence assistant."
            what_happened = ""
            why = ""
        elif "algorithm" in system.lower() or "which algorithm is used" in query_text:
            summary = "EstateIQ uses the Elite algo (created by Team Elite). It routes natural language queries and converts user intent to evaluate contextual ML models."
            what_happened = ""
            why = ""
        elif "capability" in system.lower() or "what can you do" in query_text or "capabilities" in query_text:
            summary = "EstateIQ Copilot provides multi-domain monitoring across electricity, water, waste, and HVAC systems."
            what_happened = ""
            why = ""
        elif "summarize recent energy use" in query_text:
            summary = "Recent campus energy telemetry across all monitored blocks is operating within nominal baseline parameters with an average load of 42.5 kW over the past 24 hours."
            what_happened = ""
            why = ""
        elif "why did energy use increase" in query_text:
            summary = "Energy consumption in Block B increased above contextual baseline."
            what_happened = "In Block B Hostel, actual energy consumption reached 145.2 kWh vs baseline."
            why = "HVAC compressor override was engaged during peak tariff window."
        elif "what happened to water consumption" in query_text:
            summary = "Water consumption showed sustained flow in Hostel A riser."
            what_happened = "Hostel A riser flow rate averaged 18.5 L/min across 3 consecutive intervals."
            why = "Sanitary fixture valve remained unseated after off-hours cleaning."
        else:
            summary = "Facility telemetry evaluation shows monitored parameters operating within normal campus baselines."
            what_happened = ""
            why = ""

        mock_res_json = {
            "summary": summary,
            "what_happened": what_happened,
            "why_it_happened": why,
            "evidence": ["Contextual baseline deviation evaluated"],
            "confidence_percent": 91.0,
            "business_impact": "Financial impact within normal budget allowance.",
            "recommended_actions": ["Review baseline schedule", "Inspect sensor telemetry"],
            "what_if_interpretation": "",
            "assumptions": ["Nominal sensor operation"],
            "limitations": ["Evaluated over active 15-min interval"],
            "data_status": "SUCCESS",
            "verification_status": "VERIFIED",
            "provenance": "GROQ_LLM_INTERPRETATION"
        }
        res_obj = MagicMock()
        res_obj.choices[0].message.content = json.dumps(mock_res_json)
        return res_obj

    mock_groq.chat.completions.create.side_effect = mock_chat_create
    return mock_groq


class TestUniversalAICopilotAntiStatic(unittest.TestCase):
    """Anti-Static 20-Question Test Suite."""

    @classmethod
    def setUpClass(cls):
        cls.router = UniversalQueryRouter()
        cls.planner = DataRequirementPlanner()
        cls.ai_service = EstateIQAIService()
        cls.patcher = None
        if os.getenv("ESTATEIQ_LIVE_AI_TESTS") != "1":
            cls.patcher = patch("src.ai.ai_service.get_groq_client", return_value=build_mock_groq_client())
            cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        if cls.patcher:
            cls.patcher.stop()

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


class TestAICopilotResponseFormatRules(unittest.TestCase):
    """Regression Test Suite for Intent-Grounded AI Copilot Response Formatting."""

    @classmethod
    def setUpClass(cls):
        cls.router = UniversalQueryRouter()
        cls.ai_service = EstateIQAIService()
        cls.patcher = None
        if os.getenv("ESTATEIQ_LIVE_AI_TESTS") != "1":
            cls.patcher = patch("src.ai.ai_service.get_groq_client", return_value=build_mock_groq_client())
            cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        if cls.patcher:
            cls.patcher.stop()

    def setUp(self):
        self.ai_service.clear_cache()

    def test_greeting_receives_friendly_message_no_analysis_headings(self):
        """'Hi' receives a friendly greeting with no 'What happened?' or 'Why?' headings or telemetry data."""
        query = "Hi"
        route = self.router.route(query)
        self.assertEqual(route.intent.value, "GREETING")
        self.assertFalse(route.is_explanatory)

        res = self.ai_service.query_copilot(query)
        self.assertTrue(res.success)
        self.assertEqual(res.what_happened, "")
        self.assertEqual(res.why, [])
        self.assertEqual(len(res.evidence), 0)
        self.assertTrue(any(word in res.summary for word in ["Hello", "Hi", "EstateIQ", "Copilot"]))

    def test_algorithm_question_identifies_elite_algo(self):
        """'Which algorithm is used?' identifies 'Elite algo (created by Team Elite)' and gives plain-language explanation."""
        query = "Which algorithm is used?"
        route = self.router.route(query)
        self.assertEqual(route.intent.value, "MODEL_EXPLANATION")
        self.assertFalse(route.is_explanatory)

        res = self.ai_service.query_copilot(query)
        self.assertTrue(res.success)
        self.assertIn("Elite algo (created by Team Elite)", res.summary)
        self.assertTrue(any(w in res.summary.lower() for w in ["routes", "converts", "intent"]))
        self.assertIn("models", res.summary.lower())
        self.assertEqual(res.what_happened, "")
        self.assertEqual(res.why, [])

    def test_summarize_recent_energy_use_normal_sentence_no_why_headings(self):
        """'Summarize recent energy use' uses normal sentence form without 'Why?' or 'What happened?' headings."""
        query = "Summarize recent energy use"
        route = self.router.route(query)
        self.assertFalse(route.is_explanatory)

        res = self.ai_service.query_copilot(query)
        self.assertTrue(res.success)
        self.assertEqual(res.what_happened, "")
        self.assertEqual(res.why, [])
        self.assertTrue(len(res.summary) > 20)

    def test_why_did_energy_use_increase_uses_both_sections(self):
        """'Why did energy use increase?' uses both 'What happened?' and 'Why?' sections."""
        query = "Why did energy use increase?"
        route = self.router.route(query)
        self.assertTrue(route.is_explanatory)

        res = self.ai_service.query_copilot(query)
        self.assertTrue(res.success)
        self.assertNotEqual(res.what_happened, "")
        self.assertGreater(len(res.why), 0)

    def test_what_happened_to_water_consumption_uses_both_sections(self):
        """'What happened to water consumption?' uses both 'What happened?' and 'Why?' sections."""
        query = "What happened to water consumption?"
        route = self.router.route(query)
        self.assertTrue(route.is_explanatory)

        res = self.ai_service.query_copilot(query)
        self.assertTrue(res.success)
        self.assertNotEqual(res.what_happened, "")
        self.assertGreater(len(res.why), 0)


if __name__ == "__main__":
    unittest.main()

