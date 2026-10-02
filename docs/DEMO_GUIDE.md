# 🎯 Hackathon Live Storytelling Demo Guide

Step-by-step presentation script for demonstrating **Facility Intelligence AI** to hackathon judges.

---

## 🎬 8-Step Presentation Script

1. **Step 1: Baseline Executive Dashboard**
   - Open `app.py` in Streamlit. Navigate to `🏠 Executive Dashboard`.
   - Highlight the top KPI cards (Energy, Water, Waste, AQI, Sustainability Score 78.5 Gold).
   - Show the interactive campus map overlay (GEC Smart Campus).

2. **Step 2: Inject Operational Anomaly**
   - Navigate to `🎯 Hackathon Demo Mode`.
   - Select **Step 2: Inject Energy Anomaly**.
   - Show simulated HVAC load surge in Block B Hostel (145 kWh vs 78 kWh baseline).

3. **Step 3: ML Anomaly Detector Flags High Alert**
   - Show how Isolation Forest flags an active anomaly score (`0.88`) and triggers **Priority 1 Alert** in `🚨 AI Alert Center`.

4. **Step 4: SHAP Feature Attribution ("Why?")**
   - Click "Why was this flagged?". Show SHAP feature breakdown: HVAC load (+72% impact), Ambient Temperature (+18%), Occupancy (+10%).
   - Point out the causation disclaimer.

5. **Step 5: Rule-Based & GenAI Recommendation**
   - Show the structured 7-part recommendation: *"Inspect HVAC operational schedules and setback controls in Block B Hostel."*

6. **Step 6: AI Assistant Interaction**
   - Open `🤖 AI Facility Assistant`.
   - Submit: *"Why is energy consumption high in Block B Hostel?"*
   - Show response generated from validated context with offline fallback support.

7. **Step 7: What-If Operational Simulation**
   - Open `🔬 What-If Simulation`.
   - Move HVAC schedule slider to `-15%`.
   - Show immediate computational impact: Energy drops by 18.5 kWh, CO2e emissions drop by ~15.2 kg.

8. **Step 8: Sustainability Scorecard & Impact Summary**
   - Open `📊 Sustainability Scorecard`.
   - Demonstrate overall Sustainability Index improvement from 78.5 to 82.1.
   - Conclude demo showing live API endpoints at `http://localhost:8000/docs`.
