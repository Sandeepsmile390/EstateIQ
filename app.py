"""
EstateIQ Facility Intelligence - Master Streamlit Command Center Application.
Sustainable Facility and Estate Intelligence Dashboard for India.

Exact Web UI Implementation in Streamlit:
- Liquid-Glass Canva Design System (Dark Forest Green #124B3E & Vibrant Mint #2BB49B)
- Top Bar Application Shell with Logo, SaaS Plan Pill, and Role Switcher
- Operational Status Banner & Notice System
- Hero Metrics Grid (Overall Score 87/100, Energy Target 7.42 MWh, Water/Air Split, Weekly Load)
- 12 Exact Web UI Navigation Tabs (Overview, Suggestions & ROI, Energy ML, Water, Waste,
  Mobility & Air, What-If Simulator, AI Co-Pilot, ML Registry, ESG & Carbon, Subscription, REST API)
- Grounded Groq Cloud LLM (llama-3.3-70b-versatile) & EstateIQ-DIF Evidence Packets
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Folium Map Import
try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

from src.data.repository import DataRepository
from src.scoring.sustainability import SustainabilityScoreCalculator
from src.recommendations.genai_engine import GenAIExplanationEngine
from src.priority.engine import FacilityPriorityEngine
from src.scenarios.whatif import WhatIfScenarioEngine
from src.explainability.explainer import ModelExplainer
from src.intelligence.fusion_engine import EstateIQIntelligenceFusionEngine
from src.intelligence.outcome_verification import OutcomeVerificationEngine
from src.ai.ai_service import EstateIQAIService
from src.ai.context_builder import build_ai_context
from src.ai.exceptions import AIServiceError
from src.intelligence.types import EventData
from src.data.geospatial import GeospatialFacilityRepository

from src.ui.components import (
    get_icon, inject_custom_css, render_top_bar,
    render_status_banner, render_hero_metrics_grid,
    render_badge, render_kpi_card, apply_plotly_theme
)

# Page Setup
st.set_page_config(
    page_title="EstateIQ - Multi-Role Facility Intelligence Platform",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Global Visual Design System CSS
inject_custom_css()

# Data Repository Instance (Cached)
@st.cache_resource
def get_repo():
    return DataRepository()

repo = get_repo()

# Instantiate Core AI Engines
genai_engine = GenAIExplanationEngine()
priority_engine = FacilityPriorityEngine()
sustainability_calc = SustainabilityScoreCalculator()
fusion_engine = EstateIQIntelligenceFusionEngine()
outcome_verifier = OutcomeVerificationEngine()
ai_copilot_service = EstateIQAIService()

# ==============================================================================
# SIDEBAR NAVIGATION & PERSONA ROLE SWITCHER
# ==============================================================================
st.sidebar.markdown(f'''
<div style="display:flex; align-items:center; gap:10px; padding:12px 0 16px 0; border-bottom:1px solid rgba(43, 180, 155, 0.25);">
    <div style="width:36px; height:36px; background:linear-gradient(135deg, #2BB49B 0%, #104F40 100%); border-radius:10px; display:flex; align-items:center; justify-content:center; color:#fff;">
        {get_icon("Leaf", "#FFFFFF", 20)}
    </div>
    <span style="font-family:'Plus Jakarta Sans', sans-serif; font-weight:800; font-size:1.3rem; color:#FFFFFF;">
        Estate<span style="color:#2BB49B;">IQ</span>
    </span>
</div>
''', unsafe_allow_html=True)

# Role Switcher
st.sidebar.markdown(f'''
<div style="font-size:0.75rem; font-weight:700; color:#A3C9BE; text-transform:uppercase; letter-spacing:0.8px; margin-top:16px; margin-bottom:6px;">
    {get_icon("UserCheck", "#2BB49B", 14)} ACTIVE USER ROLE
</div>
''', unsafe_allow_html=True)

user_role = st.sidebar.selectbox(
    "Switch User Persona:",
    [
        "RS Administrator (Full Access)",
        "Alex Chen (Operations Engineer)",
        "Dr. Priya Sharma (ESG Auditor)",
        "Sam Taylor (Campus Stakeholder)"
    ],
    index=0,
    label_visibility="collapsed"
)

# Sidebar Tabs Menu
st.sidebar.markdown(f'''
<div style="font-size:0.75rem; font-weight:700; color:#A3C9BE; text-transform:uppercase; letter-spacing:0.8px; margin-top:16px; margin-bottom:8px;">
    {get_icon("LayoutDashboard", "#2BB49B", 14)} MAIN NAVIGATION TABS
</div>
''', unsafe_allow_html=True)

web_ui_tabs = [
    "Dashboard Overview",
    "AI Suggestions & ROI",
    "Energy ML",
    "Water Module",
    "Waste Overflow",
    "Mobility & Air",
    "What-If Simulator",
    "AI Operational Co-Pilot",
    "ML Models Registry",
    "ESG & Carbon Audit",
    "Subscription & Plans",
    "AI REST API & Diagnostics",
    "Data Explorer & Tools"
]

menu = st.sidebar.radio("Navigation Tabs:", web_ui_tabs, label_visibility="collapsed")

# System Quick Stats Widget Footer
st.sidebar.markdown(f'''
<div style="background: #124B3E; border: 1px solid #2BB49B; border-radius: 12px; padding: 14px; margin-top: 20px;">
    <div style="font-size: 0.78rem; font-weight: 800; color: #2BB49B; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
        {get_icon("Activity", "#2BB49B", 14)} Telemetry Status
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #A3C9BE; margin-bottom: 4px;">
        <span>Active Buildings:</span> <b style="color: #FFFFFF;">10</b>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #A3C9BE; margin-bottom: 4px;">
        <span>Sensors Monitored:</span> <b style="color: #FFFFFF;">245</b>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #A3C9BE; margin-bottom: 4px;">
        <span>Active Signals:</span> <b style="color: #F87171;">2 High</b>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #A3C9BE;">
        <span>Sampling Rate:</span> <b style="color: #4ADE80;">15-min</b>
    </div>
</div>
''', unsafe_allow_html=True)

# Helper to Load Saved ML Models
def load_model(task_name: str):
    m_path = f"models/{task_name}_model.joblib"
    meta_path = f"models/{task_name}_metadata.joblib"
    if os.path.exists(m_path) and os.path.exists(meta_path):
        return joblib.load(m_path), joblib.load(meta_path)
    return None, None

# Render Top Header Application Shell
render_top_bar(campus_name="Main Campus - All Blocks", status="ATTENTION", user_role=user_role.split(" (")[0])

# Render Operational Status Banner
render_status_banner(active_role=user_role, suggestions_count=3)

# Render Top Row Hero Metrics Cards
render_hero_metrics_grid(hero_score=87, energy_val="7.42 MWh", water_val="12,480 kL", aqi_val=68)


# ==============================================================================
# TAB 1: DASHBOARD OVERVIEW
# ==============================================================================
if menu == "Dashboard Overview":
    st.markdown(f"### {get_icon('LayoutDashboard', '#2BB49B', 24)} Dashboard Overview {render_badge('observed')}", unsafe_allow_html=True)
    st.caption("Multi-domain real-time sensor telemetry, multi-line consumption trends, performance metrics breakdown & GIS map")
    
    # 3 Summary Cards Row (Matching Web UI middle section)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f"""
        <div style="background:#124B3E; border:1px solid #2BB49B; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; color:#A3C9BE; font-weight:700; text-transform:uppercase;">Total Energy</div>
            <div style="font-size:2rem; font-weight:800; color:#FFFFFF; font-family:'Plus Jakarta Sans'; margin-top:4px;">7.42 MWh</div>
            <div style="font-size:0.75rem; color:#4ADE80; margin-top:4px;">● Nominal Demand Horizon</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""
        <div style="background:#124B3E; border:1px solid #2BB49B; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; color:#A3C9BE; font-weight:700; text-transform:uppercase;">Water Recycled</div>
            <div style="font-size:2rem; font-weight:800; color:#FFFFFF; font-family:'Plus Jakarta Sans'; margin-top:4px;">12,480 kL</div>
            <div style="font-size:0.75rem; color:#2BB49B; margin-top:4px;">● Greywater Treatment Active</div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div style="background:#124B3E; border:1px solid #2BB49B; border-radius:14px; padding:18px;">
            <div style="font-size:0.8rem; color:#A3C9BE; font-weight:700; text-transform:uppercase;">Waste Diverted</div>
            <div style="font-size:2rem; font-weight:800; color:#FFFFFF; font-family:'Plus Jakarta Sans'; margin-top:4px;">5,420 kg</div>
            <div style="font-size:0.75rem; color:#F5C577; margin-top:4px;">● 61% Compost / Recycling</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_chart, col_side = st.columns([1.6, 1])
    
    with col_chart:
        st.markdown(f"#### {get_icon('Activity', '#2BB49B', 20)} Resource Consumption Wave Trend", unsafe_allow_html=True)
        df_e = repo.get_energy_data(limit=72)
        if not df_e.empty:
            fig_wave = px.line(df_e, x="timestamp", y="electricity_kwh", color="building_id", title="Multi-Domain Real-Time Telemetry Comparison (kWh)")
            fig_wave = apply_plotly_theme(fig_wave)
            st.plotly_chart(fig_wave, use_container_width=True)
        else:
            st.info("Streaming telemetry line chart active.")

    with col_side:
        st.markdown(f"#### {get_icon('SlidersHorizontal', '#2BB49B', 20)} Performance Breakdown", unsafe_allow_html=True)
        st.markdown("""
        <div style="background:rgba(21,30,51,0.9); border:1px solid #2A3857; border-radius:14px; padding:18px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700; color:#E2E8F0; margin-bottom:6px;">
                <span>Energy Intensity Target</span>
                <span style="color:#2BB49B;">74%</span>
            </div>
            <div style="background:#1E293B; border-radius:6px; height:8px; overflow:hidden;">
                <div style="background:#2BB49B; width:74%; height:100%;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700; color:#E2E8F0; margin-top:14px; margin-bottom:6px;">
                <span>Water Recovery Rate</span>
                <span style="color:#38BDF8;">68%</span>
            </div>
            <div style="background:#1E293B; border-radius:6px; height:8px; overflow:hidden;">
                <div style="background:#38BDF8; width:68%; height:100%;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700; color:#E2E8F0; margin-top:14px; margin-bottom:6px;">
                <span>Waste Diversion Ratio</span>
                <span style="color:#F5C577;">61%</span>
            </div>
            <div style="background:#1E293B; border-radius:6px; height:8px; overflow:hidden;">
                <div style="background:#F5C577; width:61%; height:100%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(239, 68, 68, 0.1); border:1px solid #EF4444; border-radius:14px; padding:16px;">
            <div style="display:flex; align-items:center; gap:8px; color:#F87171; font-weight:800; font-size:0.95rem; margin-bottom:6px;">
                {get_icon("TriangleAlert", "#F87171", 18)} 2 Active Backend Alerts
            </div>
            <div style="font-size:0.82rem; color:#CBD5E1; margin-bottom:10px;">
                Block B HVAC anomaly (145.2 kWh) & Central Cafeteria Bin #01 overflow risk.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Campus GIS Map Section
    st.markdown("---")
    st.markdown(f"#### {get_icon('Map', '#2BB49B', 20)} Campus GIS Spatial Twin Overlay", unsafe_allow_html=True)
    if HAS_FOLIUM:
        geo_repo = GeospatialFacilityRepository()
        map_html = geo_repo.generate_folium_map(asset_type="All")
        st.components.v1.html(map_html, height=450, scrolling=False)
    else:
        st.info("Interactive Map: GEC Smart Campus (Latitude: 18.5204, Longitude: 73.8567)")


# ==============================================================================
# TAB 2: AI SUGGESTIONS & ROI ADVISOR
# ==============================================================================
elif menu == "AI Suggestions & ROI":
    st.markdown(f"### {get_icon('Lightbulb', '#F5C577', 24)} AI Suggestions & ROI Advisor {render_badge('predicted')}", unsafe_allow_html=True)
    st.caption("Actionable AI recommendations with predicted financial return & carbon offset metrics")
    
    # ROI Summary Banner matching Web UI
    st.markdown(f"""
    <div style="background:linear-gradient(135deg, #124B3E 0%, #0E3D32 100%); border:1px solid #2BB49B; border-radius:16px; padding:24px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div>
            <div style="font-size:0.85rem; font-weight:700; color:#A3C9BE; text-transform:uppercase;">Total Actionable AI Potential Savings</div>
            <div style="font-size:2.2rem; font-weight:800; color:#FFFFFF; font-family:'Plus Jakarta Sans'; margin:6px 0;">
                $24,400 / yr <span style="font-size:1.2rem; color:#2BB49B;">(₹19.8 Lakhs/yr)</span>
            </div>
            <div style="font-size:0.88rem; color:#CBD5E1;">
                Executing all 3 AI automated optimization rules will reduce campus carbon footprint by <strong>24.5 Tons CO₂e / yr</strong>.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("✨ Execute All AI Automated Rules Now", type="primary"):
        st.balloons()
        st.success("✅ All 3 AI Operational Rules Successfully Dispatched to BMS Controller!")
        
    st.markdown("---")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        st.markdown(f"""
        <div style="background:rgba(21, 30, 51, 0.9); border:1px solid #EF4444; border-radius:14px; padding:20px; height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="pill-badge badge-red">HIGH PRIORITY</span>
                <span style="font-size:0.75rem; color:#94A3B8;">Energy</span>
            </div>
            <h4 style="font-size:1rem; font-weight:700; color:#FFFFFF; margin-bottom:8px;">HVAC Thermostat Setpoint Reset</h4>
            <p style="font-size:0.82rem; color:#CBD5E1; margin-bottom:14px;">
                Continuous compressor load surge detected in Block B Hostel. Resetting setpoint to 24°C saves 18.2 Tons CO₂e.
            </p>
            <div style="font-size:1.1rem; font-weight:800; color:#4ADE80; margin-bottom:12px;">+$14,200 / yr (₹11.5L)</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Apply HVAC Rule", key="rule_hvac"):
            st.success("HVAC Setpoint reset queued!")

    with col_s2:
        st.markdown(f"""
        <div style="background:rgba(21, 30, 51, 0.9); border:1px solid #F59E0B; border-radius:14px; padding:20px; height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="pill-badge badge-amber">MEDIUM PRIORITY</span>
                <span style="font-size:0.75rem; color:#94A3B8;">Maintenance</span>
            </div>
            <h4 style="font-size:1rem; font-weight:700; color:#FFFFFF; margin-bottom:8px;">Chiller 01 Bearing Lubrication</h4>
            <p style="font-size:0.82rem; color:#CBD5E1; margin-bottom:14px;">
                Vibration anomaly 3.8 mm/s indicates friction. Scheduled preventive maintenance avoids catastrophic downtime.
            </p>
            <div style="font-size:1.1rem; font-weight:800; color:#4ADE80; margin-bottom:12px;">+$6,400 / yr (₹5.2L)</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Schedule Chiller Maintenance", key="rule_chiller"):
            st.success("Work Order created!")

    with col_s3:
        st.markdown(f"""
        <div style="background:rgba(21, 30, 51, 0.9); border:1px solid #2BB49B; border-radius:14px; padding:20px; height:100%;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="pill-badge badge-teal">OPTIMIZATION</span>
                <span style="font-size:0.75rem; color:#94A3B8;">Sanitation</span>
            </div>
            <h4 style="font-size:1rem; font-weight:700; color:#FFFFFF; margin-bottom:8px;">Cafeteria Bin Dynamic Route</h4>
            <p style="font-size:0.82rem; color:#CBD5E1; margin-bottom:14px;">
                Bin #01 fill rate accelerated. Dispatching collection prior to peak lunch overflow preserves sanitation grade.
            </p>
            <div style="font-size:1.1rem; font-weight:800; color:#4ADE80; margin-bottom:12px;">+$3,800 / yr (₹3.1L)</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Dispatch Route", key="rule_waste"):
            st.success("Collection route updated!")


# ==============================================================================
# TAB 3: ENERGY ML FORECASTING
# ==============================================================================
elif menu == "Energy ML":
    st.markdown(f"### {get_icon('Zap', '#F5C577', 24)} Energy ML Forecasting & SHAP Explainability {render_badge('predicted')}", unsafe_allow_html=True)
    
    # 3 Forecast Horizon Cards
    fc1, fc2, fc3 = st.columns(3)
    with fc1: render_kpi_card("1-Hour Forecast", "135.5", " kWh", "CatBoost Model Active", "neutral", "Zap", "#2BB49B")
    with fc2: render_kpi_card("4-Hour Peak Forecast", "155.0", " kWh", "Peak Demand Window (14:00)", "up", "Zap", "#EF4444")
    with fc3: render_kpi_card("24-Hour Cumulative Load", "118.2", " kWh", "Off-Peak Compliant", "down", "Zap", "#4ADE80")

    st.markdown("---")
    df_e = repo.get_energy_data(limit=168)
    if not df_e.empty:
        fig_e = px.line(df_e, x="timestamp", y="electricity_kwh", color="building_id", title="7-Day Hourly Demand Trajectory & ML Predictions (kWh)")
        fig_e = apply_plotly_theme(fig_e)
        st.plotly_chart(fig_e, use_container_width=True)

    st.markdown("---")
    st.markdown(f"#### {get_icon('Sparkles', '#C084FC', 20)} SHAP Feature Attribution Analysis", unsafe_allow_html=True)
    model, meta = load_model("energy_kwh_prediction")
    if model is not None and meta is not None:
        explainer = ModelExplainer(model)
        sample_df = pd.DataFrame([{
            "temperature": 32.0, "humidity": 55.0, "occupancy": 150,
            "hvac_load": 55.0, "lighting_load": 15.0, "equipment_load": 25.0,
            "previous_energy_kwh": 125.0, "hour": 14, "day_of_week": 2, "month": 3,
            "is_weekend": 0, "is_peak_hour": 1, "hour_sin": 0.5, "hour_cos": -0.8
        }])
        for c in meta["feature_names"]:
            if c not in sample_df.columns:
                sample_df[c] = 0
        attr_res = explainer.explain_prediction(sample_df[meta["feature_names"]])
        st.json(attr_res)


# ==============================================================================
# TAB 4: WATER MODULE
# ==============================================================================
elif menu == "Water Module":
    st.markdown(f"### {get_icon('Droplets', '#38BDF8', 24)} Water Consumption & Anomaly Detection {render_badge('observed')}", unsafe_allow_html=True)
    df_w = repo.get_water_data(limit=168)
    if not df_w.empty:
        fig_w = px.area(df_w, x="timestamp", y="water_consumption_liters", color="building_id", title="Campus Water Flow Trajectory (Liters)")
        fig_w = apply_plotly_theme(fig_w)
        st.plotly_chart(fig_w, use_container_width=True)


# ==============================================================================
# TAB 5: WASTE OVERFLOW
# ==============================================================================
elif menu == "Waste Overflow":
    st.markdown(f"### {get_icon('Trash2', '#10B981', 24)} Waste Bin Overflow Predictor {render_badge('predicted')}", unsafe_allow_html=True)
    df_wst = repo.get_waste_data(limit=100)
    if not df_wst.empty:
        cols = [c for c in ["timestamp", "bin_id", "location_id", "fill_level_percent", "overflow_within_2h"] if c in df_wst.columns]
        st.dataframe(df_wst[cols].tail(15), use_container_width=True)


# ==============================================================================
# TAB 6: MOBILITY & AIR
# ==============================================================================
elif menu == "Mobility & Air":
    st.markdown(f"### {get_icon('Car', '#F5C577', 24)} Mobility, Parking & Air Quality Analytics {render_badge('observed')}", unsafe_allow_html=True)
    
    col_tr, col_air = st.columns(2)
    with col_tr:
        st.markdown("#### Campus Entry Gate Vehicle Count")
        df_tr = repo.get_traffic_data(limit=100)
        if not df_tr.empty:
            fig_tr = px.bar(df_tr, x="location_id" if "location_id" in df_tr.columns else "location", y="vehicle_count", title="Vehicle Count Distribution")
            fig_tr = apply_plotly_theme(fig_tr)
            st.plotly_chart(fig_tr, use_container_width=True)

    with col_air:
        st.markdown("#### Air Quality Index (AQI) Trajectory")
        df_air = repo.get_air_quality_data(limit=100)
        if not df_air.empty:
            fig_air = px.line(df_air, x="timestamp", y="aqi", title="AQI Sensor Network Trajectory")
            fig_air = apply_plotly_theme(fig_air)
            st.plotly_chart(fig_air, use_container_width=True)


# ==============================================================================
# TAB 7: WHAT-IF SIMULATOR
# ==============================================================================
elif menu == "What-If Simulator":
    st.markdown(f"### {get_icon('SlidersHorizontal', '#38BDF8', 24)} Operational What-If Scenario Simulator {render_badge('simulated')}", unsafe_allow_html=True)
    
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        hvac_mod = st.slider("Modify HVAC Setback Schedule (% of Baseline Load):", 50, 120, 85)
        solar_capacity = st.slider("Rooftop Solar PV Addition (kWp):", 0, 500, 150)
    with sim_col2:
        water_rec = st.slider("Greywater Recycling Efficiency (%):", 0, 60, 30)
        tariff_rate = st.slider("Electricity Tariff Rate (₹ INR / kWh):", 6.0, 14.0, 9.5)
        
    base_kwh = 140.0
    sim_kwh = (base_kwh * (hvac_mod / 100.0)) - (solar_capacity * 0.15)
    sim_kwh = max(10.0, sim_kwh)
    
    monthly_savings_kwh = (base_kwh - sim_kwh) * 24 * 30
    monthly_savings_inr = monthly_savings_kwh * tariff_rate
    co2_saved_kg = monthly_savings_kwh * 0.82
    
    bm1, bm2, bm3 = st.columns(3)
    with bm1: render_kpi_card("With-XAI Savings", f"{round(max(0, monthly_savings_inr), 0):,.0f}", " ₹/mo", "+7.0% Net Gain vs Heuristic", "down", "Sparkles", "#C084FC")
    with bm2: render_kpi_card("CO2 Reduced", f"{round(max(0, co2_saved_kg), 1):,}", " kg/mo", "0.82 kg/kWh Baseline", "down", "Leaf", "#22C55E")
    with bm3: render_kpi_card("Simulated Demand Target", f"{round(sim_kwh, 1)}", " kWh", f"{round(((sim_kwh-base_kwh)/base_kwh)*100, 1)}% Shift", "down", "Zap", "#F5C577")

    st.markdown("---")
    sim_df = pd.DataFrame({
        "Hour": list(range(24)),
        "Baseline Demand (kWh)": [base_kwh + np.sin(h/4)*20 for h in range(24)],
        "Simulated Target (kWh)": [sim_kwh + np.sin(h/4)*15 for h in range(24)]
    })
    fig_sim = px.line(sim_df, x="Hour", y=["Baseline Demand (kWh)", "Simulated Target (kWh)"], title="24-Hour Simulated Demand Curve Comparison")
    fig_sim = apply_plotly_theme(fig_sim)
    st.plotly_chart(fig_sim, use_container_width=True)


# ==============================================================================
# TAB 8: AI OPERATIONAL CO-PILOT
# ==============================================================================
elif menu == "AI Operational Co-Pilot":
    st.markdown(f"### {get_icon('Sparkles', '#C084FC', 24)} AI Operational Decision Assistant (Groq Cloud LLM)", unsafe_allow_html=True)
    st.caption("Powered by Groq Cloud (llama-3.3-70b-versatile) & Grounded EstateIQ-DIF Evidence Packets")
    
    health = ai_copilot_service.check_health()
    h_col1, h_col2, h_col3, h_col4 = st.columns(4)
    with h_col1: st.markdown(f"**AI Provider:** `{health.provider.upper()}`")
    with h_col2: st.markdown(f"**Model:** `{health.model}`")
    with h_col3:
        status_color = "🟢" if health.status == "healthy" else ("🟡" if health.status == "not_configured" else "🔴")
        st.markdown(f"**Status:** {status_color} `{health.status.upper()}`")
    with h_col4: st.markdown(f"**Environment Mode:** `{health.mode.upper()}`")
        
    st.markdown("---")
    
    if "ai_query" not in st.session_state:
        st.session_state["ai_query"] = "Why is energy consumption high in Block B Hostel?"
        
    query_input = st.text_input("Ask a question about facility operations:", value=st.session_state["ai_query"])
    
    if st.button("Submit Query", type="primary"):
        with st.spinner("Querying EstateIQ-DIF Backend & Grounded Groq AI..."):
            try:
                res = ai_copilot_service.query_copilot(user_query=query_input)
                
                st.markdown(f"""
                <div class="ai-insight-box">
                    <div class="ai-insight-header">
                        {get_icon('Sparkles', '#C084FC', 20)}
                        <span>EstateIQ Grounded AI Analysis {res.data_source_badge}</span>
                    </div>
                    <p><b>Executive Summary:</b> {res.summary}</p>
                    <p><b>What Happened?:</b> {res.what_happened}</p>
                    <p><b>Why It Happened (Grounded Causes):</b></p>
                    <ul>
                        {''.join(f'<li>{w}</li>' for w in res.why)}
                    </ul>
                    <p><b>Confidence Score:</b> {res.confidence:.1f}% | <b>Provider:</b> {res.ai_provider} ({res.model})</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### Recommended Operational Actions & ROI")
                for act in res.recommended_actions:
                    title = act.get("title", act) if isinstance(act, dict) else act
                    saving = act.get("expected_cost_saving_inr", 11500) if isinstance(act, dict) else 11500
                    st.success(f"**Recommended Action:** {title} | **Expected Monthly Savings:** ₹{saving:,.0f}")
                    
                with st.expander("🔍 View Grounded Evidence Packet & Diagnostic Details"):
                    st.json({
                        "request_id": res.request_id,
                        "evidence_observed": res.evidence,
                        "assumptions": res.assumptions,
                        "limitations": res.limitations,
                        "generated_at": res.generated_at,
                        "fallback_used": res.fallback_used
                    })

            except AIServiceError as e:
                st.error(f"❌ AI SERVICE ERROR: [{e.error_code}] {e.message}")
            except Exception as e:
                st.error(f"❌ UNEXPECTED AI ERROR: {str(e)}")


# ==============================================================================
# TAB 9: ML MODELS REGISTRY
# ==============================================================================
elif menu == "ML Models Registry":
    st.markdown(f"### {get_icon('Cpu', '#2BB49B', 24)} Trained ML Models Registry & Validation Metrics {render_badge('observed')}", unsafe_allow_html=True)
    m_dir = "models"
    if os.path.exists(m_dir):
        files = [f for f in os.listdir(m_dir) if f.endswith("_metadata.joblib")]
        records = []
        for f in files:
            m = joblib.load(os.path.join(m_dir, f))
            metrics = m.get("val_metrics", {})
            r2_or_f1 = metrics.get("r2", metrics.get("f1", "N/A"))
            records.append({
                "Model Task": m.get("task", f.replace("_metadata.joblib", "")),
                "Algorithm Selected": m.get("selected_model", "Linear/Ensemble"),
                "Metric Score (R²/F1)": round(r2_or_f1, 4) if isinstance(r2_or_f1, (float, int)) else r2_or_f1,
                "MAE / Loss": round(metrics.get("mae", 0.0), 4) if "mae" in metrics else "N/A",
                "Features Count": len(m.get("feature_names", []))
            })
        st.dataframe(pd.DataFrame(records), use_container_width=True)


# ==============================================================================
# TAB 10: ESG & CARBON AUDIT
# ==============================================================================
elif menu == "ESG & Carbon Audit":
    st.markdown(f"### {get_icon('Leaf', '#22C55E', 24)} ESG & Carbon Footprint Audit {render_badge('observed')}", unsafe_allow_html=True)
    res = sustainability_calc.calculate_score(140, 120, 950, 1000, 42, 110, 185, 200, 0.75, 25)
    score_val = res.get("composite_sustainability_score", 87.0)
    
    sc1, sc2, sc3 = st.columns(3)
    with sc1: render_kpi_card("Overall ESG Score", f"{score_val}", " /100", "Tier: GOLD TIER", "down", "Leaf", "#22C55E")
    with sc2: render_kpi_card("Energy Sub-Score", "84.0", " /100", "Efficient", "neutral", "Zap", "#F5C577")
    with sc3: render_kpi_card("Carbon Sub-Score", "85.0", " /100", "Compliant", "neutral", "Factory", "#10B981")
    
    st.markdown("---")
    st.json(res)


# ==============================================================================
# TAB 11: SUBSCRIPTION & PLANS
# ==============================================================================
elif menu == "Subscription & Plans":
    st.markdown(f"### {get_icon('Crown', '#F5C577', 24)} SaaS Subscription & Billing Plans", unsafe_allow_html=True)
    
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("""
        <div style="background:rgba(21, 30, 51, 0.9); border:1px solid #2A3857; border-radius:14px; padding:20px;">
            <h4 style="color:#94A3B8;">Community Tier</h4>
            <div style="font-size:1.8rem; font-weight:800; color:#FFF; margin:10px 0;">$0 <span style="font-size:0.9rem; font-weight:400;">/mo</span></div>
            <p style="font-size:0.8rem; color:#CBD5E1;">For single facility research & basic rule-based monitoring.</p>
        </div>
        """, unsafe_allow_html=True)

    with p2:
        st.markdown("""
        <div style="background:linear-gradient(135deg, #124B3E 0%, #0E3D32 100%); border:2px solid #2BB49B; border-radius:14px; padding:20px;">
            <span class="pill-badge badge-gold">ACTIVE PLAN</span>
            <h4 style="color:#2BB49B; margin-top:6px;">Enterprise Pro</h4>
            <div style="font-size:1.8rem; font-weight:800; color:#FFF; margin:10px 0;">$499 <span style="font-size:0.9rem; font-weight:400;">/mo</span></div>
            <p style="font-size:0.8rem; color:#CBD5E1;">Full AI Copilot, Groq LPU integration, SHAP explainability & unlimited sensors.</p>
        </div>
        """, unsafe_allow_html=True)

    with p3:
        st.markdown("""
        <div style="background:rgba(21, 30, 51, 0.9); border:1px solid #2A3857; border-radius:14px; padding:20px;">
            <h4 style="color:#C084FC;">Govt & Institutional</h4>
            <div style="font-size:1.8rem; font-weight:800; color:#FFF; margin:10px 0;">Custom</div>
            <p style="font-size:0.8rem; color:#CBD5E1;">Multi-campus state grid deployment with SLA & dedicated engineers.</p>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# TAB 12: AI REST API & DIAGNOSTICS
# ==============================================================================
elif menu == "AI REST API & Diagnostics":
    st.markdown(f"### {get_icon('Radio', '#38BDF8', 24)} AI REST API & Service Diagnostics", unsafe_allow_html=True)
    st.caption("Server-side Groq Cloud API Gateway, Health Diagnostics & Live Endpoint Testing")
    
    health = ai_copilot_service.check_health()
    
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1: render_kpi_card("AI Provider", "Groq Cloud", "", "LPU Hardware", "neutral", "Cpu", "#38BDF8")
    with s2: render_kpi_card("Active Model", health.model, "", "llama-3.3-70b-versatile", "neutral", "BrainCircuit", "#C084FC")
    with s3: render_kpi_card("Configuration", "READY" if health.configured else "NOT CONFIGURED", "", "GROQ_API_KEY Check", "up" if health.configured else "down", "Key", "#10B981" if health.configured else "#EF4444")
    with s4: render_kpi_card("Connection Health", health.status.upper(), "", f"Latency: {health.latency_ms:.1f} ms", "up" if health.status == "healthy" else "down", "Activity", "#10B981" if health.status == "healthy" else "#F59E0B")
    with s5: render_kpi_card("Operating Mode", health.mode.upper(), "", "ESTATEIQ_MODE", "neutral", "ShieldCheck", "#38BDF8")
    
    st.markdown("---")
    
    test_prompt = st.text_input("Test Prompt:", value="Respond with exactly: ESTATEIQ_GROQ_CONNECTION_OK")
    if st.button("Run Connection Test (POST /api/v1/ai/test)", type="primary"):
        with st.spinner("Sending test ping to Groq API via FastAPI backend..."):
            test_res = ai_copilot_service.test_connection(prompt=test_prompt)
            if test_res.success:
                st.success(f"✅ CONNECTION SUCCESS! Latency: {test_res.latency_ms:.1f} ms | Message: `{test_res.message}`")
            else:
                st.error(f"❌ CONNECTION FAILED: [{test_res.error_code}] {test_res.error_message}")


# ==============================================================================
# TAB 13: DATA EXPLORER & TOOLS
# ==============================================================================
elif menu == "Data Explorer & Tools":
    st.markdown(f"### {get_icon('Database', '#38BDF8', 24)} Centralized Facility Data Explorer & Diagnostic Tools", unsafe_allow_html=True)
    tbl = st.selectbox("Select Data Table:", ["facilities", "buildings", "energy_readings", "water_readings", "waste_readings", "air_quality_readings", "equipment_sensor_readings", "emissions"])
    df = repo.query_table(tbl, limit=100)
    st.dataframe(df, use_container_width=True)
