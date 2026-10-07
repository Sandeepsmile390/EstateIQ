"""
Pydantic Response Schemas for Groq AI Service (src/ai/schemas.py).
Enforces structured outputs and validates AI responses against schema contracts.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CopilotResponse(BaseModel):
    """Structured AI Copilot Response Schema."""
    summary: str = Field(description="High-level natural language summary of the facility observation.")
    what_happened: str = Field(description="Objective explanation of observed telemetry behavior.")
    why_it_happened: str = Field(description="Grounded explanation of underlying drivers derived from SHAP/context.")
    evidence: List[str] = Field(default_factory=list, description="List of grounded evidence points from DIF backend.")
    confidence_percent: float = Field(default=0.0, description="Confidence score (0-100%) from ECI engine.")
    business_impact: str = Field(description="Financial cost surge (₹/year) and carbon impact summary.")
    recommended_actions: List[str] = Field(default_factory=list, description="Ranked action recommendations.")
    what_if_interpretation: str = Field(default="", description="Interpretation of scenario simulation results.")
    assumptions: List[str] = Field(default_factory=list, description="Explicit assumptions used in analysis.")
    limitations: List[str] = Field(default_factory=list, description="Known operational limitations.")
    data_status: str = Field(default="SUCCESS", description="Telemetry data status (SUCCESS, SYNTHETIC, INSUFFICIENT_DATA).")
    verification_status: str = Field(default="PENDING", description="Outcome verification status.")
    provenance: str = Field(default="GROQ_LLM_INTERPRETATION", description="Data provenance marker.")

class AnomalyExplanationResponse(BaseModel):
    """Structured Anomaly Explanation Schema."""
    headline: str
    detailed_explanation: str
    primary_drivers: List[Dict[str, Any]]
    confidence_level: str
    cost_of_inaction_summary: str
    recommended_next_step: str

class WhatIfInterpretationResponse(BaseModel):
    """Structured What-If Scenario Interpretation Schema."""
    scenario_title: str
    current_state_summary: str
    scenario_state_summary: str
    projected_savings_summary: str
    co2_reduction_summary: str
    risk_assessment: str
    verification_guidance: str
