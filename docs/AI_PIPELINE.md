# 🤖 AI & GenAI Pipeline Documentation

Documentation for Explainable AI (SHAP), Priority Engine, and GenAI Action Engine.

---

## 🔍 1. SHAP Explainability (XAI)

For supported tree and linear regression models, `src/explainability/explainer.py` calculates local SHAP attributions:
- Ranks top feature contributions (e.g. Occupancy, Temperature, HVAC load, Hour).
- ⚠️ **Mandatory Disclaimer**: SHAP feature attributions indicate how features influenced the model prediction; they do NOT establish direct physical causation.

---

## 🚨 2. Platform Operational Priority Engine

`src/priority/engine.py` combines four operational factors into a transparent composite score:

$$\text{Priority Score} = w_1 \cdot \text{Severity} + w_2 \cdot \text{Probability} + w_3 \cdot \text{Impact} + w_4 \cdot \text{Urgency}$$

- **Priority 1 (URGENT)**: Score $\ge 0.70$
- **Priority 2 (MODERATE)**: Score $0.40 \text{ to } 0.69$
- **Priority 3 (LOW)**: Score $< 0.40$

---

## 💬 3. GenAI Action Engine & Offline Fallback

`src/recommendations/genai_engine.py` formats validated ML inputs into a 7-part operational summary:
1. *What happened?*
2. *What is predicted?*
3. *Why was it flagged?*
4. *Severity*
5. *Recommended action*
6. *Assumptions*
7. *Limitations*

🔒 **Grounding Mandate**: GenAI NEVER invents measurements, probabilities, sensor values, financial savings, or health claims!

If `OPENAI_API_KEY` or `GENAI_API_KEY` is not present, the system falls back to a deterministic rule-based engine:
- **Status Output**: `GenAI: Offline | Rule-based insights: Active`
