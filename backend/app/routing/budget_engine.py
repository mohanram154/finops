from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# ============================================================================
# Budget Schemas
# ============================================================================
class BudgetStatus(BaseModel):
    department: str
    currency: str = "INR"  # Supports INR / USD
    daily_budget: float
    monthly_budget: float
    current_spend: float
    remaining_budget: float
    spend_percentage: float
    status: str  # "active", "warning", "exceeded"

class BudgetCheckResult(BaseModel):
    can_afford: bool
    department: str
    estimated_cost: float
    remaining_budget: float
    current_spend: float
    monthly_budget: float
    message: str

# ============================================================================
# In-Memory Departmental Budget Tracking
# ============================================================================
DEFAULT_DEPARTMENT_BUDGETS: Dict[str, Dict[str, float]] = {
    "finance": {
        "monthly_budget": 1000.0,
        "daily_budget": 50.0,
        "current_spend": 620.0  # Example from specification: 1000 budget, 620 spent, 380 remaining
    },
    "engineering": {
        "monthly_budget": 3500.0,
        "daily_budget": 150.0,
        "current_spend": 1240.0
    },
    "hr": {
        "monthly_budget": 600.0,
        "daily_budget": 30.0,
        "current_spend": 180.0
    },
    "marketing": {
        "monthly_budget": 1800.0,
        "daily_budget": 80.0,
        "current_spend": 750.0
    },
    "general": {
        "monthly_budget": 2000.0,
        "daily_budget": 100.0,
        "current_spend": 500.0
    }
}

# ============================================================================
# Budget Engine
# ============================================================================
class BudgetEngine:
    """
    Tracks departmental spend vs allocated budgets.
    Prevents execution of models whose projected cost breaches remaining budget limits.
    """

    _budgets: Dict[str, Dict[str, float]] = {k: v.copy() for k, v in DEFAULT_DEPARTMENT_BUDGETS.items()}

    @classmethod
    def reset(cls):
        cls._budgets = {k: v.copy() for k, v in DEFAULT_DEPARTMENT_BUDGETS.items()}

    @classmethod
    def get_budget_status(cls, department: str, custom_override: Optional[Dict[str, float]] = None) -> BudgetStatus:
        dept_key = department.lower().strip() if department else "general"

        if custom_override and "monthly_budget" in custom_override:
            m_budget = float(custom_override["monthly_budget"])
            c_spend = float(custom_override.get("current_spend", 0.0))
            d_budget = float(custom_override.get("daily_budget", m_budget / 30.0))
        elif dept_key in cls._budgets:
            b = cls._budgets[dept_key]
            m_budget = b["monthly_budget"]
            c_spend = b["current_spend"]
            d_budget = b.get("daily_budget", m_budget / 30.0)
        else:
            b = cls._budgets["general"]
            m_budget = b["monthly_budget"]
            c_spend = b["current_spend"]
            d_budget = b.get("daily_budget", m_budget / 30.0)

        remaining = max(0.0, round(m_budget - c_spend, 4))
        spend_pct = round((c_spend / m_budget * 100.0), 1) if m_budget > 0 else 100.0

        if remaining <= 0:
            status = "exceeded"
        elif spend_pct >= 85.0:
            status = "warning"
        else:
            status = "active"

        return BudgetStatus(
            department=dept_key,
            currency="INR",
            daily_budget=d_budget,
            monthly_budget=m_budget,
            current_spend=c_spend,
            remaining_budget=remaining,
            spend_percentage=spend_pct,
            status=status
        )

    @classmethod
    def check_budget(
        cls,
        department: str,
        estimated_cost: float,
        custom_override: Optional[Dict[str, float]] = None
    ) -> BudgetCheckResult:
        status = cls.get_budget_status(department, custom_override)
        can_afford = estimated_cost <= status.remaining_budget

        if can_afford:
            msg = f"Budget verified: estimated cost {status.currency} {estimated_cost:.4f} is within remaining budget {status.currency} {status.remaining_budget:.2f}."
        else:
            msg = f"Budget constraint failure: estimated cost {status.currency} {estimated_cost:.4f} exceeds remaining budget {status.currency} {status.remaining_budget:.2f}."

        return BudgetCheckResult(
            can_afford=can_afford,
            department=status.department,
            estimated_cost=estimated_cost,
            remaining_budget=status.remaining_budget,
            current_spend=status.current_spend,
            monthly_budget=status.monthly_budget,
            message=msg
        )

    @classmethod
    def record_spend(cls, department: str, amount: float) -> None:
        dept_key = department.lower().strip() if department else "general"
        if dept_key in cls._budgets:
            cls._budgets[dept_key]["current_spend"] += amount

