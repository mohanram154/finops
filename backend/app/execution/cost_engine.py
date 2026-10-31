from typing import Dict, Any
from pydantic import BaseModel, Field

class CostAccountingResult(BaseModel):
    model: str
    tier: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    pricing_type: str = "Simulated Enterprise Pricing"
    currency: str = "INR"

class BaselineComparison(BaseModel):
    baseline_model: str = "advanced"
    baseline_cost: float
    optimized_cost: float
    savings: float
    savings_percentage: float
    cost_per_successful_outcome: float

class CostEngine:
    """
    Computes precise token accounting and financial pricing.
    Supports simulated enterprise rates:
    Small: ₹0.01 / 1k
    Medium: ₹0.05 / 1k
    Advanced: ₹0.20 / 1k
    """

    PRICING_TABLE = {
        "small": {"input_rate": 0.01, "output_rate": 0.01},
        "medium": {"input_rate": 0.05, "output_rate": 0.05},
        "advanced": {"input_rate": 0.20, "output_rate": 0.20}
    }

    @classmethod
    def calculate(
        cls,
        model: str,
        tier: str,
        input_tokens: int,
        output_tokens: int
    ) -> CostAccountingResult:
        t_key = (tier or "medium").lower()
        rates = cls.PRICING_TABLE.get(t_key, cls.PRICING_TABLE["medium"])

        total_tokens = input_tokens + output_tokens
        input_cost = round((input_tokens / 1000.0) * rates["input_rate"], 4)
        output_cost = round((output_tokens / 1000.0) * rates["output_rate"], 4)
        total_cost = round(input_cost + output_cost, 4)

        return CostAccountingResult(
            model=model,
            tier=t_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            pricing_type="Simulated Enterprise Pricing",
            currency="INR"
        )

    @classmethod
    def compare_with_baseline(
        cls,
        optimized_cost: float,
        total_tokens: int,
        successful_requests: int = 1,
        total_requests: int = 1
    ) -> BaselineComparison:
        """
        Compares actual routed cost against an all-Advanced unoptimized baseline.
        """
        # Baseline assumes Advanced tier pricing (₹0.20 per 1k tokens)
        baseline_rate = cls.PRICING_TABLE["advanced"]["output_rate"]
        baseline_cost = round((total_tokens / 1000.0) * baseline_rate, 4)

        # Baseline cost should be at least equal to optimized cost
        baseline_cost = max(baseline_cost, optimized_cost)

        savings = round(max(0.0, baseline_cost - optimized_cost), 4)
        savings_pct = round((savings / baseline_cost * 100.0), 1) if baseline_cost > 0 else 0.0

        # Cost per successful outcome
        succ = max(1, successful_requests)
        cost_per_success = round(optimized_cost / succ, 4)

        return BaselineComparison(
            baseline_model="advanced",
            baseline_cost=baseline_cost,
            optimized_cost=optimized_cost,
            savings=savings,
            savings_percentage=savings_pct,
            cost_per_successful_outcome=cost_per_success
        )

