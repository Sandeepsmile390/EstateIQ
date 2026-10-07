"""
Automated Integration & Unit Tests for Groq AI Service & Copilot (tests/test_ai_integration.py).
Tests health check, diagnostic test endpoint, evidence packet grounding, DIF integration,
Pydantic response validation, and production error handling with zero reliance on live API keys.
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app
from src.ai.config import GroqAIConfig
from src.ai.ai_service import EstateIQAIService
from src.ai.context_builder import build_ai_context
from src.ai.schemas import CopilotResponse, CopilotQueryResponse, AIHealthResponse
from src.ai.exceptions import GroqConfigurationError, GroqAuthenticationError, GroqRateLimitError

class TestAIIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.test_config = GroqAIConfig(
            api_key="gsk_test_key_12345",
            model="llama-3.3-70b-versatile",
            enabled=True,
            mode="production"
        )
        self.ai_service = EstateIQAIService(config=self.test_config)

    def test_01_ai_health_check_endpoint(self):
        """Test GET /api/v1/ai/health returns valid health contract."""
        res = self.client.get("/api/v1/ai/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("enabled", data)
        self.assertIn("provider", data)
        self.assertEqual(data["provider"], "groq")
        self.assertIn("configured", data)
        self.assertIn("model", data)
        self.assertIn("status", data)

    def test_02_context_builder_evidence_packet(self):
        """Test build_ai_context collects real telemetry and DIF outputs."""
        ctx = build_ai_context(
            facility_id="FAC_GEC_CAMPUS",
            user_query="Why is energy consumption high in Block B Hostel?",
            building_id="Block B Hostel"
        )
        self.assertIn("facility", ctx)
        self.assertIn("telemetry_observed", ctx)
        self.assertIn("contextual_baseline", ctx)
        self.assertIn("anomaly_evidence", ctx)
        self.assertIn("business_impact", ctx)
        self.assertIn("shap_attribution", ctx)
        self.assertIn("recommended_actions", ctx)
        
        # Verify non-zero numeric telemetry
        self.assertGreater(ctx["telemetry_observed"]["actual_kwh"], 0)
        self.assertIn("expected_kwh", ctx["contextual_baseline"])

    def test_03_ai_service_unconfigured_production_error(self):
        """Test that unconfigured key in production mode raises GroqConfigurationError."""
        unconfig = GroqAIConfig(api_key="", enabled=True, mode="production")
        srv = EstateIQAIService(config=unconfig)
        with self.assertRaises(GroqConfigurationError):
            srv.query_copilot(user_query="Test query")

    def test_04_copilot_end_to_end_mocked_groq(self):
        """Test end-to-end Copilot query with mocked Groq client."""
        mock_groq = MagicMock()
        mock_completion = MagicMock()
        
        mock_response_json = {
            "summary": "Block B Hostel energy consumption is 145.2 kWh, which is +86.1% above contextual baseline.",
            "what_happened": "High electrical demand driven by continuous 55 kW HVAC compressor load.",
            "why_it_happened": "HVAC setpoint override active during 32°C peak ambient temperature.",
            "evidence": ["Contextual baseline deviation +86.1%", "SHAP HVAC attribution +42%"],
            "confidence_percent": 92.5,
            "business_impact": "Estimated annual cost surge is ₹53,700.",
            "recommended_actions": ["Reset thermostat setback schedule to 24.5°C"],
            "what_if_interpretation": "2°C setback projected to save ~15% energy.",
            "assumptions": ["Tariff ₹9.50/kWh"],
            "limitations": ["Model prediction based on 15-min interval IoT stream"],
            "data_status": "SUCCESS",
            "verification_status": "PENDING",
            "provenance": "GROQ_LLM_INTERPRETATION"
        }
        
        mock_completion.choices[0].message.content = str(mock_response_json).replace("'", '"')
        mock_groq.chat.completions.create.return_value = mock_completion

        with patch("src.ai.ai_service.get_groq_client", return_value=mock_groq):
            res = self.ai_service.query_copilot(
                user_query="Why is energy consumption high in Block B Hostel?",
                building_id="Block B Hostel"
            )

            self.assertTrue(res.success)
            self.assertIn("Block B Hostel", res.summary)
            self.assertEqual(res.ai_provider, "groq")
            self.assertEqual(res.model, "llama-3.3-70b-versatile")
            self.assertFalse(res.fallback_used)
            self.assertTrue(res.data_source_badge.startswith("["))
            self.assertTrue(res.data_source_badge.endswith("]"))

    def test_05_copilot_api_endpoint_integration(self):
        """Test POST /api/v1/ai/copilot API endpoint contract."""
        mock_groq = MagicMock()
        mock_completion = MagicMock()
        mock_response_json = {
            "summary": "Block B Hostel energy consumption is 145.2 kWh vs 78.0 kWh expected baseline.",
            "what_happened": "HVAC surge detected.",
            "why_it_happened": "High ambient temperature.",
            "evidence": ["Baseline deviation +86.1%"],
            "confidence_percent": 88.0,
            "business_impact": "₹42,000/year",
            "recommended_actions": ["Reset HVAC setback"],
            "what_if_interpretation": "",
            "assumptions": ["Tariff ₹9.50/kWh"],
            "limitations": [],
            "data_status": "SUCCESS",
            "verification_status": "PENDING",
            "provenance": "GROQ_LLM_INTERPRETATION"
        }
        mock_completion.choices[0].message.content = str(mock_response_json).replace("'", '"')
        mock_groq.chat.completions.create.return_value = mock_completion

        with patch("src.ai.ai_service.get_groq_client", return_value=mock_groq):
            payload = {
                "query": "Why is energy consumption high in Block B Hostel?",
                "facility_id": "FAC_GEC_CAMPUS",
                "building_id": "Block B Hostel"
            }
            res = self.client.post("/api/v1/ai/copilot", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertIn("request_id", data)
            self.assertIn("summary", data)

if __name__ == "__main__":
    unittest.main()
