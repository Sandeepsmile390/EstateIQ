# EstateIQ Groq AI Copilot & AI Integration Architecture

---

## 1. EXECUTIVE SUMMARY

EstateIQ integrates **Groq Cloud Infrastructure** (`llama-3.3-70b-versatile`) as an explainability, interpretation, and executive reasoning layer sitting directly **ABOVE** specialized machine learning models and the **EstateIQ-DIF (Dynamic Intelligence Fusion)** quantitative decision engine.

```text
SPECIALIST ML ENGINES (XGBoost / Prophet / Isolation Forest / SHAP)
                     │
                     ▼
          ESTATEIQ-DIF DECISION ENGINE
                     │
                     ▼
     GROUNDED EVIDENCE PACKET (JSON Schema)
                     │
                     ▼
             GROQ AI COPILOT
```

---

## 2. CRITICAL SECRET MANAGEMENT & PRIVACY

- **Environment-Based Configuration**: The Groq API key is loaded strictly via `GROQ_API_KEY` in `.env`.
- **Git Exclusions**: `.env` is listed in `.gitignore` and is never committed to source control.
- **Frontend Protection**: The Groq API client is executed **ONLY** on the FastAPI backend (`src/ai/groq_client.py`). Raw API keys are never sent to frontend JavaScript, HTML, or logs.
- **Graceful Fallback**: If `GROQ_API_KEY` is missing or disabled (`GROQ_ENABLED=false`), EstateIQ operates seamlessly in **Deterministic Fallback Mode**.

---

## 3. ANTI-HALLUCINATION & EVIDENCE GROUNDING

Groq AI does **NOT** independently invent numeric energy readings, financial costs (₹), carbon footprints, or predictions.

### Grounding Workflow:
1. User submits a prompt (e.g., *"Why is Block B energy demand high?"*).
2. `EstateIQAIService` executes `EstateIQDIF` backend analysis.
3. `AIEvidenceBuilder` compiles a structured JSON evidence packet containing actual observed kWh, expected baseline, SHAP feature attributions, model consensus votes, confidence percentages, and cost calculations.
4. System prompt enforces strict evidence compliance:
   - If evidence is missing, output: `INSUFFICIENT DATA`.
   - If confidence $<60\%$, output: `LOW CONFIDENCE`.
   - If scenario is simulated, output: `SIMULATED SCENARIO`.
5. Response is parsed and validated against Pydantic schema contracts (`CopilotResponse`).

---

## 4. AI ENDPOINTS & OBSERVABILITY

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/ai/copilot` | `POST` | Interrogates AI Copilot with grounded facility evidence |
| `/api/v1/ai/health` | `GET` | Returns AI service availability, latency, and fallback status |

---

## 5. AI RESPONSE CACHING & RATE LIMITING

- **Evidence Hash Caching**: Identical evidence packets reuse cached Groq responses to minimize API latency and token consumption.
- **Throttling & Retries**: `GroqClientManager` handles exponential retries and request throttling. API keys are masked in all logs.
