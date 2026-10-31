from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ============================================================================
# What-If Simulation Schemas
# ============================================================================
class SimulateRequest(BaseModel):
    prompt: str
    required_quality: float = Field(90.0, ge=50.0, le=100.0)
    department: Optional[str] = "general"
    latency_requirement: Optional[str] = None

class ModelTierComparison(BaseModel):
    tier: str  # "SMALL", "MEDIUM", "ADVANCED"
    model_name: str
    estimated_tokens: int
    estimated_cost: float
    estimated_quality: float
    estimated_latency_ms: float
    is_valid: bool
    status_label: str  # "VALID" or "INVALID"
    reason: str

class SimulateResponse(BaseModel):
    prompt: str
    required_quality: float
    comparisons: List[ModelTierComparison]
    recommended_tier: str
    recommended_model: str
    recommendation_reason: str
    estimated_savings_vs_advanced: float
    savings_percentage: float

# ============================================================================
# What-If Model Simulator Engine
# ============================================================================
class ModelSimulator:
    """
    Evaluates what-if trade-offs between SMALL, MEDIUM, and ADVANCED model tiers
    for any prompt and quality requirement.
    """

    TIER_SPECS = {
        "SMALL": {
            "model_name": "Small Model (GPT-4o Mini / Gemini Flash)",
            "rate_per_1k": 0.01,
            "quality": 88.0,
            "latency_ms": 100.0
        },
        "MEDIUM": {
            "model_name": "Medium Model (GPT-4o / Claude 3.5 Sonnet)",
            "rate_per_1k": 0.05,
            "quality": 93.0,
            "latency_ms": 200.0
        },
        "ADVANCED": {
            "model_name": "Advanced Model (o1-preview / Claude 3 Opus)",
            "rate_per_1k": 0.20,
            "quality": 97.0,
            "latency_ms": 400.0
        }
    }

    @classmethod
    def simulate(cls, prompt: str, required_quality: float = 90.0) -> SimulateResponse:
        in_tokens = max(1, len(prompt) // 4)
        out_tokens = max(20, in_tokens * 2)
        total_tokens = in_tokens + out_tokens

        comparisons: List[ModelTierComparison] = []
        valid_tiers: List[str] = []

        for tier in ["SMALL", "MEDIUM", "ADVANCED"]:
            spec = cls.TIER_SPECS[tier]
            cost = round((total_tokens / 1000.0) * spec["rate_per_1k"], 4)
            quality = spec["quality"]
            latency = spec["latency_ms"]

            is_valid = quality >= required_quality
            if is_valid:
                valid_tiers.append(tier)
                reason = f"Quality {quality:.0f}% meets required threshold ({required_quality:.0f}%)."
            else:
                reason = f"Quality {quality:.0f}% is below required threshold ({required_quality:.0f}%)."

            comparisons.append(ModelTierComparison(
                tier=tier,
                model_name=spec["model_name"],
                estimated_tokens=total_tokens,
                estimated_cost=cost,
                estimated_quality=quality,
                estimated_latency_ms=latency,
                is_valid=is_valid,
                status_label="VALID" if is_valid else "INVALID",
                reason=reason
            ))

        # Pick recommended tier: lowest cost valid model
        if valid_tiers:
            # Order of cost: SMALL, then MEDIUM, then ADVANCED
            recommended_tier = valid_tiers[0]
            if recommended_tier == "SMALL":
                rec_reason = "Small is the lowest-cost model that satisfies the quality requirement."
            elif recommended_tier == "MEDIUM":
                rec_reason = "Medium is the lowest-cost model that satisfies the quality requirement (Small rejected due to quality threshold)."
            else:
                rec_reason = "Advanced is required to satisfy the strict quality requirement (Small and Medium both below threshold)."
        else:
            # No tier strictly satisfies (e.g. required quality 98%)
            recommended_tier = "ADVANCED"
            rec_reason = "Advanced selected as highest capability tier, though quality threshold is exceptionally high."

        # Compute savings vs Advanced
        adv_cost = round((total_tokens / 1000.0) * cls.TIER_SPECS["ADVANCED"]["rate_per_1k"], 4)
        rec_cost = round((total_tokens / 1000.0) * cls.TIER_SPECS[recommended_tier]["rate_per_1k"], 4)
        savings = round(max(0.0, adv_cost - rec_cost), 4)
        savings_pct = round((savings / adv_cost * 100.0), 1) if adv_cost > 0 else 0.0

        return SimulateResponse(
            prompt=prompt,
            required_quality=required_quality,
            comparisons=comparisons,
            recommended_tier=recommended_tier,
            recommended_model=cls.TIER_SPECS[recommended_tier]["model_name"],
            recommendation_reason=rec_reason,
            estimated_savings_vs_advanced=savings,
            savings_percentage=savings_pct
        )

