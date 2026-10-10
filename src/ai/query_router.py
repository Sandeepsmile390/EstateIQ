"""
Universal Query Router (src/ai/query_router.py).
Fast, deterministic intent classification engine mapping user natural language queries
to domain intents, analytical targets, entity extractions, and data retrieval scopes.
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum

class IntentCategory(str, Enum):
    GREETING = "GREETING"
    SYSTEM_CAPABILITY = "SYSTEM_CAPABILITY"
    PROJECT_EXPLANATION = "PROJECT_EXPLANATION"
    FACILITY_OVERVIEW = "FACILITY_OVERVIEW"
    ELECTRICITY = "ELECTRICITY"
    ENERGY = "ENERGY"
    TRANSFORMER = "TRANSFORMER"
    DG = "DG"
    HVAC = "HVAC"
    OCCUPANCY = "OCCUPANCY"
    WATER = "WATER"
    WASTE = "WASTE"
    AIR_QUALITY = "AIR_QUALITY"
    TRAFFIC = "TRAFFIC"
    PARKING = "PARKING"
    EQUIPMENT = "EQUIPMENT"
    SAFETY = "SAFETY"
    ASSETS = "ASSETS"
    EMISSIONS = "EMISSIONS"
    SUSTAINABILITY = "SUSTAINABILITY"
    ANOMALY = "ANOMALY"
    FORECAST = "FORECAST"
    TREND = "TREND"
    COMPARISON = "COMPARISON"
    RECOMMENDATION = "RECOMMENDATION"
    PRIORITY_ACTION = "PRIORITY_ACTION"
    FINANCIAL_IMPACT = "FINANCIAL_IMPACT"
    WHAT_IF = "WHAT_IF"
    MODEL_EXPLANATION = "MODEL_EXPLANATION"
    DATA_QUALITY = "DATA_QUALITY"
    IOT_STATUS = "IOT_STATUS"
    DATASET = "DATASET"
    UNKNOWN = "UNKNOWN"

class QueryRouteResult:
    def __init__(
        self,
        intent: IntentCategory,
        confidence: float = 0.95,
        primary_domain: str = "general",
        target_building: Optional[str] = None,
        time_horizon: str = "latest",
        is_multi_domain: bool = False,
        extracted_entities: Dict[str, Any] = None,
        is_explanatory: bool = False
    ):
        self.intent = intent
        self.confidence = confidence
        self.primary_domain = primary_domain
        self.target_building = target_building
        self.time_horizon = time_horizon
        self.is_multi_domain = is_multi_domain
        self.extracted_entities = extracted_entities or {}
        self.is_explanatory = is_explanatory

    @property
    def category(self) -> str:
        return self.intent.value if hasattr(self.intent, "value") else str(self.intent)

class UniversalQueryRouter:
    """Classifies user queries into discrete operational intents and data retrieval plans."""

    GREETING_PATTERNS = [
        r"^(hi|hello|hey|greetings|good\s+morning|good\s+afternoon|good\s+evening)$",
        r"^hi\s+there$",
        r"^hello\s+there$",
        r"^hey\s+there$"
    ]

    ALGORITHM_PATTERNS = [
        r"which\s+algorithm",
        r"what\s+algorithm",
        r"algorithm\s+(is\s+)?used",
        r"how\s+does\s+(the\s+)?(algorithm|ai|copilot)\s+work",
        r"who\s+created\s+the\s+algorithm",
        r"what\s+ml\s+model",
        r"what\s+ai\s+algorithm"
    ]

    EXPLANATORY_PATTERNS = [
        r"\bwhy\b",
        r"\bwhat\s+happened\b",
        r"\bwhat\s+caused\b",
        r"\bhow\s+come\b",
        r"\bcause\s+of\b",
        r"\breason\s+for\b"
    ]

    CAPABILITY_PATTERNS = [
        r"what\s+can\s+you\s+do",
        r"what\s+are\s+your\s+capabilities",
        r"what\s+can\s+(estateiq|ai)\s+do",
        r"how\s+can\s+you\s+help",
        r"what\s+can\s+i\s+ask",
        r"list\s+capabilities",
        r"help\s+me"
    ]

    PROJECT_PATTERNS = [
        r"what\s+is\s+estateiq",
        r"how\s+does\s+estateiq\s+work",
        r"explain\s+architecture",
        r"what\s+is\s+dif",
        r"what\s+is\s+estateiq-dif",
        r"explain\s+(estateiq-)?dif",
        r"problem\s+statement",
        r"what\s+hardware"
    ]

    IOT_PATTERNS = [
        r"sensors?\s+(online|status|healthy|value|reading|data|telemetry)",
        r"are\s+sensors\s+online",
        r"device\s+status",
        r"iot\s+(health|status|sensor|data|telemetry|value|reading|monitor)",
        r"live\s+iot",
        r"real\s+iot",
        r"sensor\s+(reading|value|data|telemetry|status)",
        r"connected\s+sensor",
        r"telemetry\s+(value|reading|data)"
    ]

    DATASET_PATTERNS = [
        r"what\s+data\s+do\s+you",
        r"dataset",
        r"telemetry\s+records",
        r"available\s+data"
    ]

    PRIORITY_PATTERNS = [
        r"what\s+should\s+i\s+(do|fix)\s+first",
        r"highest\s+priority",
        r"top\s+priority",
        r"most\s+urgent",
        r"where\s+to\s+start"
    ]

    RECOMMENDATION_PATTERNS = [
        r"what\s+should\s+i\s+do",
        r"recommend",
        r"suggest",
        r"opportunity",
        r"opportunities",
        r"saving",
        r"reduce\s+cost"
    ]

    WHAT_IF_PATTERNS = [
        r"what\s+if",
        r"simulate",
        r"setback",
        r"if\s+we\s+reduce",
        r"scenario"
    ]

    OVERVIEW_PATTERNS = [
        r"executive\s+summary",
        r"today'?s\s+summary",
        r"facility\s+overview",
        r"overall\s+status",
        r"campus\s+status",
        r"biggest\s+problem",
        r"all\s+problems"
    ]

    def route(self, query: str) -> QueryRouteResult:
        return self.route_query(query)

    def route_query(self, query: str) -> QueryRouteResult:
        if not query or not query.strip():
            return QueryRouteResult(IntentCategory.SYSTEM_CAPABILITY, 1.0, "system", is_explanatory=False)

        q = query.strip().lower()

        # Extract target building if explicitly named
        building = self._extract_building(q)

        # Check for greeting first
        for p in self.GREETING_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.GREETING, 1.0, "system", is_explanatory=False)

        # Check for algorithm question
        for p in self.ALGORITHM_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.MODEL_EXPLANATION, 0.98, "models", building, is_explanatory=False)

        # Determine if query asks for explanation / cause
        is_explanatory = any(re.search(p, q) for p in self.EXPLANATORY_PATTERNS)

        # 1. System Capabilities
        for p in self.CAPABILITY_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.SYSTEM_CAPABILITY, 0.98, "system", is_explanatory=False)

        # 2. Project Explanation
        for p in self.PROJECT_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.PROJECT_EXPLANATION, 0.95, "project", is_explanatory=is_explanatory)

        # 2b. IoT Sensor Status
        for p in self.IOT_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.IOT_STATUS, 0.95, "data_quality", building, is_explanatory=is_explanatory)

        # 2c. Dataset Metadata
        for p in self.DATASET_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.DATASET, 0.95, "dataset", building, is_explanatory=is_explanatory)

        # 3. Priority Action ("What should I fix first?")
        for p in self.PRIORITY_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.PRIORITY_ACTION, 0.95, "recommendations", building, is_explanatory=is_explanatory)

        # 4. What-If Simulation
        for p in self.WHAT_IF_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.WHAT_IF, 0.95, "simulation", building, is_explanatory=is_explanatory)

        # 5. Executive Overview / Cross-Domain
        for p in self.OVERVIEW_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.FACILITY_OVERVIEW, 0.95, "facility", building, is_multi_domain=True, is_explanatory=is_explanatory)

        # 6. Specific Domain Matching
        if any(k in q for w in ["water", "flow", "leak", "stp", "greywater"] for k in [w]):
            return QueryRouteResult(IntentCategory.WATER, 0.95, "water", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["waste", "bin", "overflow", "garbage", "trash", "recycle"] for k in [w]):
            return QueryRouteResult(IntentCategory.WASTE, 0.95, "waste", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["air", "aqi", "pm2", "pm10", "co2_ppm", "pollution", "ventilation"] for k in [w]):
            return QueryRouteResult(IntentCategory.AIR_QUALITY, 0.95, "air_quality", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["traffic", "gate", "vehicle", "car count", "congestion"] for k in [w]):
            return QueryRouteResult(IntentCategory.TRAFFIC, 0.95, "traffic", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["parking", "lot", "bay", "ev charger", "parked"] for k in [w]):
            return QueryRouteResult(IntentCategory.PARKING, 0.95, "parking", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["chiller", "ahu", "pump", "vibration", "bearing", "equipment", "asset", "machine"] for k in [w]):
            return QueryRouteResult(IntentCategory.EQUIPMENT, 0.95, "equipment", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["safety", "hazard", "incident", "egress", "emergency"] for k in [w]):
            return QueryRouteResult(IntentCategory.SAFETY, 0.95, "safety", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["carbon", "emission", "scope 1", "scope 2", "greenhouse", "co2e", "offset", "solar"] for k in [w]):
            return QueryRouteResult(IntentCategory.EMISSIONS, 0.95, "emissions", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["esg", "sustainability", "scorecard", "sdg", "grade"] for k in [w]):
            return QueryRouteResult(IntentCategory.SUSTAINABILITY, 0.95, "sustainability", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["model", "shap", "xgboost", "catboost", "isolation forest", "prophet", "algorithm"] for k in [w]):
            return QueryRouteResult(IntentCategory.MODEL_EXPLANATION, 0.95, "models", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["data quality", "coverage", "completeness", "sensor reliability", "sensor status", "sensor online"] for k in [w]):
            return QueryRouteResult(IntentCategory.DATA_QUALITY, 0.95, "data_quality", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["compare", "versus", "vs", "which building"] for k in [w]):
            return QueryRouteResult(IntentCategory.COMPARISON, 0.95, "comparison", building, is_multi_domain=True, is_explanatory=is_explanatory)

        if any(k in q for w in ["forecast", "future", "tomorrow", "predict", "horizon"] for k in [w]):
            return QueryRouteResult(IntentCategory.FORECAST, 0.95, "forecast", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["trend", "history", "historical", "over time", "past"] for k in [w]):
            return QueryRouteResult(IntentCategory.TREND, 0.95, "trend", building, is_explanatory=is_explanatory)

        if any(k in q for w in ["anomaly", "anomalies", "spike", "outlier", "deviat"] for k in [w]):
            return QueryRouteResult(IntentCategory.ANOMALY, 0.95, "anomaly", building, is_explanatory=True)

        # 7. Recommendations
        for p in self.RECOMMENDATION_PATTERNS:
            if re.search(p, q):
                return QueryRouteResult(IntentCategory.RECOMMENDATION, 0.92, "recommendations", building, is_explanatory=is_explanatory)

        # 8. Electricity / Energy
        if any(k in q for w in ["electricity", "energy", "kwh", "power", "hvac", "load", "kw"] for k in [w]):
            return QueryRouteResult(IntentCategory.ELECTRICITY, 0.92, "energy", building, is_explanatory=is_explanatory)

        # Fallback to general facility overview if unmatched
        return QueryRouteResult(IntentCategory.FACILITY_OVERVIEW, 0.70, "facility", building, is_multi_domain=True, is_explanatory=is_explanatory)

    def _extract_building(self, query_lower: str) -> Optional[str]:
        if "block b" in query_lower or "hostel b" in query_lower:
            return "Block B Hostel"
        elif "block a" in query_lower or "academic block" in query_lower:
            return "Block A Academic"
        elif "hostel a" in query_lower:
            return "Hostel A"
        elif "cafeteria" in query_lower:
            return "Central Cafeteria"
        elif "admin" in query_lower:
            return "Admin Block"
        elif "science" in query_lower:
            return "Science & Tech Complex"
        return None
