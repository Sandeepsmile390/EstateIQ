"""
EstateIQ-DIF Data Types & Schema Definitions (src/intelligence/types.py).
Defines strongly-typed dataclasses for all DIF pipeline stages.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

class ExecutionPath(str, Enum):
    FAST_PATH = "PATH_A_FAST"
    INTELLIGENCE_PATH = "PATH_B_INTELLIGENCE"
    CRITICAL_PATH = "PATH_C_CRITICAL"

class AnomalyLevel(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PriorityLevel(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"

@dataclass
class EventData:
    event_id: str
    facility_id: str
    building_id: str
    timestamp: str
    actual_kwh: float
    hour: int
    day_of_week: int
    occupancy: int
    temperature: float
    hvac_load: float = 0.0
    extra_features: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityResult:
    overall_quality_score: float
    completeness: float
    freshness: float
    consistency: float
    sensor_reliability: float
    is_insufficient: bool = False

@dataclass
class ContextualResult:
    expected_kwh: float
    std_dev: float
    residual_kwh: float
    relative_deviation_pct: float
    contextual_score: float
    early_exit: bool
    early_exit_reason: str = ""

@dataclass
class PredictionResult:
    champion_prediction: float
    champion_model: str
    challenger_predictions: Dict[str, float] = field(default_factory=dict)
    models_executed: List[str] = field(default_factory=list)

@dataclass
class AnomalyResult:
    anomaly_score: float
    anomaly_level: AnomalyLevel
    evidence: List[str]
    model_agreement_pct: float

@dataclass
class ConfidenceResult:
    confidence_pct: float
    confidence_level: str
    gate_passed: bool

@dataclass
class ImpactResult:
    surge_kwh: float
    hourly_avoidable_cost_inr: float
    daily_avoidable_cost_inr: float
    annual_cost_of_inaction_inr: float
    daily_co2_surge_kg: float
    annual_co2_surge_tons: float
    tariff_source: str = "Configured Tariff (₹9.50/kWh)"
    emission_factor_source: str = "CEA Grid Factor (0.82 kg/kWh)"

@dataclass
class RiskResult:
    risk_score: float
    risk_level: str
    risk_factors: List[str]

@dataclass
class OpportunityResult:
    opportunity_id: str
    title: str
    estimated_annual_saving_inr: float
    estimated_co2_reduction_tons: float
    effort: str
    payback_months: float

@dataclass
class RecommendationCandidate:
    action_id: str
    title: str
    description: str
    expected_energy_saving_pct: float
    expected_cost_saving_inr: float
    expected_co2_reduction_tons: float
    implementation_cost_inr: float
    effort: str
    operational_risk: str
    confidence_pct: float
    utility_score: float = 0.0

@dataclass
class DecisionResult:
    event_id: str
    trace_id: str
    execution_path: ExecutionPath
    quality: QualityResult
    contextual: ContextualResult
    prediction: Optional[PredictionResult]
    anomaly: AnomalyResult
    confidence: ConfidenceResult
    impact: ImpactResult
    risk: RiskResult
    opportunities: List[OpportunityResult]
    decision_score: float
    priority: PriorityLevel
    recommendations: List[RecommendationCandidate]
    shap_attribution: List[Dict[str, Any]] = field(default_factory=list)
    models_skipped: List[str] = field(default_factory=list)
    provenance: str = "ESTATEIQ_DIF"
