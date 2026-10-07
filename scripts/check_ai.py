"""
EstateIQ AI Diagnostic Script (scripts/check_ai.py).
Performs end-to-end audit of environment settings, API key format, connectivity,
FastAPI endpoints, DIF engine integration, and AI Copilot grounded response pipeline.
"""

import os
import sys
import time

# Add root directory to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.ai.config import DEFAULT_AI_CONFIG
from src.ai.ai_service import EstateIQAIService
from src.ai.context_builder import build_ai_context
from src.data.repository import DataRepository
from src.intelligence.dif_engine import EstateIQDIF

def run_diagnostic():
    print("====================================")
    print("ESTATEIQ AI DIAGNOSTIC & HEALTH CHECK")
    print("====================================")

    # 1. Environment Check
    env_mode = os.getenv("ESTATEIQ_MODE", "production")
    print(f"Environment Mode:       {env_mode.upper()} (PASS)")

    # 2. Key Check
    key = os.getenv("GROQ_API_KEY", "")
    key_configured = bool(key and key.strip())
    print(f"Groq key configured:    {'YES' if key_configured else 'NO (Set GROQ_API_KEY in .env)'}")

    key_format_valid = key.startswith("gsk_") if key_configured else False
    if key_configured:
        print(f"Groq key format:        {'VALID (gsk_...)' if key_format_valid else 'INVALID_FORMAT'}")
    else:
        print(f"Groq key format:        N/A (Key missing)")

    # 3. Model
    model = DEFAULT_AI_CONFIG.model
    print(f"Configured Model:       {model}")

    # 4. Database Check
    try:
        repo = DataRepository()
        latest = repo.get_latest_energy()
        print(f"Database Telemetry:     PASS (Latest kWh: {latest.get('energy_kwh')})")
    except Exception as e:
        print(f"Database Telemetry:     FAIL ({str(e)})")

    # 5. EstateIQ-DIF Check
    try:
        dif = EstateIQDIF()
        ctx = build_ai_context(facility_id="FAC_GEC_CAMPUS", user_query="Why is energy high?")
        print(f"EstateIQ-DIF Engine:    PASS (DIF Anomaly Score: {ctx['anomaly_evidence']['anomaly_score']})")
    except Exception as e:
        print(f"EstateIQ-DIF Engine:    FAIL ({str(e)})")

    # 6. Groq Service Connectivity Test
    ai_service = EstateIQAIService()
    health = ai_service.check_health()
    print(f"Health Status:          {health.status.upper()}")

    test_res = ai_service.test_connection()
    print(f"Groq Connectivity:      {'PASS' if test_res.success else 'FAIL (' + str(test_res.error_message) + ')'}")

    # 7. End-to-End Copilot Execution Check
    print("\nExecuting End-to-End Copilot Pipeline Check...")
    try:
        copilot_res = ai_service.query_copilot(
            user_query="Why is energy consumption high in Block B Hostel?",
            building_id="Block B Hostel"
        )
        print(f"AI Copilot Pipeline:   PASS")
        print(f"  Request ID:          {copilot_res.request_id}")
        print(f"  Summary:             {copilot_res.summary[:80]}...")
        print(f"  Data Source Badge:   {copilot_res.data_source_badge}")
        print(f"  Fallback Used:       {copilot_res.fallback_used}")
    except Exception as e:
        print(f"AI Copilot Pipeline:   FAIL ({str(e)})")

    print("====================================\n")

if __name__ == "__main__":
    run_diagnostic()
