# EstateIQ Groq AI Copilot & AI Integration Architecture

---

## 1. EXECUTIVE SUMMARY

EstateIQ integrates **Groq Cloud Infrastructure** (`llama-3.3-70b-versatile`) as an explainability, interpretation, and executive reasoning layer sitting directly **ABOVE** specialized machine learning models and the **EstateIQ-DIF (Dynamic Intelligence Fusion)** quantitative decision engine.

```text
PHYSICAL / SIMULATED TELEMETRY ──► FASTAPI ──► DATA REPOSITORY
                                                   │
                                                   ▼
SPECIALIST ML ENGINES (XGBoost / Prophet / Isolation Forest / SHAP)
                                                   │
                                                   ▼
                     ESTATEIQ-DIF DECISION ENGINE
                                                   │
                                                   ▼
                 AI CONTEXT BUILDER (Evidence Packet JSON)
                                                   │
                                                   ▼
                         GROQ AI COPILOT
                                                   │
                                                   ▼
                   PYDANTIC RESPONSE VALIDATION
                                                   │
                                                   ▼
                         STREAMLIT / WEB UI
```

---

## 2. CRITICAL SECRET MANAGEMENT & PRIVACY

- **Environment-Based Configuration**: The Groq API key is loaded strictly via `GROQ_API_KEY` in `.env`.
- **Git Exclusions**: `.env` is listed in `.gitignore` and is never committed to source control.
- **Frontend Protection**: The Groq API client is executed **ONLY** on the FastAPI backend (`src/ai/groq_client.py`). Raw API keys are never sent to frontend JavaScript, HTML, or logs.
- **Production Mode Security (`ESTATEIQ_MODE=production`)**: If `GROQ_API_KEY` is missing or fails in production mode, EstateIQ returns explicit structured errors (`AI SERVICE ERROR`), preventing silent hardcoded demo responses.

---

## 3. ANTI-HALLUCINATION & EVIDENCE GROUNDING

Groq AI does **NOT** independently invent numeric energy readings, financial costs (₹), carbon footprints, or predictions.

### Grounding Workflow:
1. User submits a prompt (e.g., *"Why is Block B energy demand high?"*).
2. `AIContextBuilder` (`src/ai/context_builder.py`) queries `DataRepository` for latest telemetry and runs `EstateIQDIF` backend analysis.
3. A structured JSON evidence packet is compiled containing actual observed kWh, contextual expected baseline, SHAP feature attributions, model consensus votes, confidence percentages, and cost calculations.
4. If the query asks for What-If scenario impact, `WhatIfScenarioEngine` is invoked dynamically before constructing the evidence.
5. System prompt enforces strict evidence compliance:
   - If evidence is missing, output: `INSUFFICIENT DATA`.
   - If confidence $<60\%$, output: `LOW CONFIDENCE`.
   - If scenario is simulated, output: `SIMULATED SCENARIO`.
6. Response is parsed and validated against Pydantic schema contracts (`CopilotResponse`, `CopilotQueryResponse`).

---

## 4. AI ENDPOINTS & DIAGNOSTICS

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/ai/copilot` | `POST` | Interrogates AI Copilot with grounded facility evidence packet |
| `/api/v1/ai/chat` | `POST` | User query endpoint delegating to EstateIQAIService |
| `/api/v1/ai/health` | `GET` | Returns AI service availability, status, model, mode, and latency |
| `/api/v1/ai/test` | `POST` | Executes minimal live ping test to Groq API gateway |

---

## 5. DIAGNOSTICS & SYSTEM AUDIT

Run the automated AI diagnostic tool to verify environment setup, key format, connectivity, DIF integration, and end-to-end pipeline execution:

```bash
python scripts/check_ai.py
```

---

## 6. AUTOMATED INTEGRATION TESTS

Run the automated integration test suite:

```bash
python -m unittest tests/test_ai_integration.py
```
