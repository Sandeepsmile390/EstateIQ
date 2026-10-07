"""
Recommendation Ranker (src/intelligence/recommendation_ranker.py).
Ranks candidate recommendations using a multi-attribute utility function with normalized dimensions.
"""

from typing import List, Dict, Any
from src.intelligence.types import RecommendationCandidate

class RecommendationRanker:
    """Ranks candidate recommendations using normalized utility scoring."""

    def rank(
        self,
        candidates: List[RecommendationCandidate]
    ) -> List[RecommendationCandidate]:
        if not candidates:
            return []

        # Find maximum bounds for normalization
        max_cost_saving = max([c.expected_cost_saving_inr for c in candidates] + [1.0])
        max_co2 = max([c.expected_co2_reduction_tons for c in candidates] + [1.0])
        max_impl_cost = max([c.implementation_cost_inr for c in candidates] + [1.0])

        for c in candidates:
            norm_benefit = (c.expected_cost_saving_inr / max_cost_saving) * 40.0
            norm_sustainability = (c.expected_co2_reduction_tons / max_co2) * 20.0
            norm_confidence = (c.confidence_pct / 100.0) * 20.0

            effort_penalty = 15.0 if c.effort == "HIGH" else (8.0 if c.effort == "MEDIUM" else 2.0)
            risk_penalty = 15.0 if c.operational_risk == "HIGH" else (8.0 if c.operational_risk == "MEDIUM" else 2.0)
            cost_penalty = (c.implementation_cost_inr / max_impl_cost) * 10.0

            utility = round(
                norm_benefit + norm_sustainability + norm_confidence - (effort_penalty + risk_penalty + cost_penalty), 1
            )
            c.utility_score = max(0.0, utility)

        # Sort descending by utility_score
        return sorted(candidates, key=lambda x: x.utility_score, reverse=True)
