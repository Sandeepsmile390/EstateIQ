"""
Pydantic Response Schemas for Groq AI Service (src/ai/schemas.py).
Enforces structured outputs and validates AI responses against schema contracts.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CopilotQueryRequest(BaseModel):
    """Incoming request payload for AI Copilot."""
    query: Optional[str] = Field(None, description="User's query string.")
    message: Optional[str] = Field(None, description="Alternative message field for compatibility.")
    facility_id: str = Field("FAC_GEC_CAMPUS", description="Target facility identifier.")
    building_id: Optional[str] = Field("Block B Hostel", description="Target building identifier.")
    actual_kwh: Optional[float] = Field(None, description="Optional telemetry input.")

    @property
    def user_query(self) -> str:
        return self.query or self.message or "Why is electricity consumption high?"

class CopilotResponse(BaseModel):
    """Internal Structured AI Copilot Response Schema from Groq LLM."""
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

class CopilotQueryResponse(BaseModel):
    """API Response Contract for POST /api/v1/ai/copilot."""
    success: bool = Field(True, description="Indicates if the query succeeded.")
    request_id: str = Field(description="Unique request identifier.")
    response: str = Field(description="Formatted natural language response text.")
    summary: str = Field(description="High-level summary.")
    what_happened: str = Field(description="What happened in telemetry.")
    why: List[str] = Field(default_factory=list, description="Grounded causes.")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Structured evidence packet list.")
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Actions with expected savings.")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions.")
    limitations: List[str] = Field(default_factory=list, description="Limitations.")
    confidence: float = Field(0.0, description="Confidence percentage.")
    data_status: str = Field("SUCCESS", description="Data status string.")
    ai_provider: str = Field("groq", description="AI provider name.")
    model: str = Field(description="AI model name.")
    generated_at: str = Field(description="ISO timestamp of analysis.")
    fallback_used: bool = Field(False, description="Whether fallback response engine was invoked.")
    data_source_badge: str = Field("[SIMULATED IoT]", description="Data provenance badge.")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error diagnostics if failed.")

class AIHealthResponse(BaseModel):
    """API Response Contract for GET /api/v1/ai/health."""
    enabled: bool
    provider: str = "groq"
    configured: bool
    model: str
    status: str  # healthy, disabled, not_configured, unauthorized, rate_limited, timeout, provider_error, unknown_error
    latency_ms: float
    mode: str = "production"

class AITestRequest(BaseModel):
    """Payload for live test request."""
    prompt: Optional[str] = Field("Respond with exactly: ESTATEIQ_GROQ_CONNECTION_OK")

class AITestResponse(BaseModel):
    """API Response Contract for POST /api/v1/ai/test."""
    success: bool
    provider: str = "groq"
    model: str
    message: str
    latency_ms: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = False

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
