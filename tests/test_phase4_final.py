import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import app, get_root_health, get_budgets, get_policies
from app.execution import global_pipeline, global_cache, ChatRequest
from app.finops import ModelSimulator, FinOpsAdvisor, AnalyticsEngine
from app.routing.budget_engine import BudgetEngine


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean cache, budget, and policies before each test."""
    global_cache.clear()
    FinOpsAdvisor.reset_policies()
    BudgetEngine.reset()
    yield
    global_cache.clear()
    FinOpsAdvisor.reset_policies()
    BudgetEngine.reset()
    


def test_1_root_health_endpoint():
    """Verify GET /health returns required specification format."""
    res = get_root_health()
    assert res["status"] == "healthy"
    assert res["service"] == "nexus-ai-finops"
    assert res["mode"] in ["simulation", "ollama", "real"]
    assert res["database"] in ["connected", "healthy"]
    assert res["cache"] == "available"
    assert res["models"] >= 3


def test_2_budget_and_policies_endpoints():
    """Verify GET /api/v1/budget and GET /api/v1/policies endpoints."""
    # Budgets
    budgets = get_budgets(department=None)
    assert "engineering" in budgets
    assert "finance" in budgets
    assert budgets["finance"].monthly_budget == 1000.0

    # Specific department
    fin_budget = get_budgets(department="finance")
    assert fin_budget.department == "finance"

    # Policies
    policies = get_policies(department=None)
    assert "policies" in policies
    assert "engineering" in policies["policies"]


def test_3_scenario_1_simple_request():
    """
    SCENARIO 1: Simple Request
    Translate this sentence into Tamil: 'AI is changing the future of software development.'
    """
    prompt = 'Translate this sentence into Tamil: "AI is changing the future of software development."'
    req = ChatRequest(prompt=prompt, department="Engineering", required_quality=80.0)
    res = global_pipeline.execute(req)

    assert res.success is True
    assert res.selected_model.lower() == "small"
    assert res.final_model.lower() == "small"
    assert res.cost > 0.0
    assert res.cost < 0.01  # Small rate ₹0.01/1k
    assert res.quality_score >= 80.0
    assert res.latency_ms > 0


def test_4_scenario_2_complex_request():
    """
    SCENARIO 2: Complex Request
    Analyze financial risk of enterprise AI system processing customer data.
    """
    prompt = (
        "Analyze the financial risk of an enterprise AI system that processes "
        "customer data and recommend a secure cost optimization strategy."
    )
    req = ChatRequest(
        prompt=prompt,
        department="Finance",
        priority="HIGH",
        sensitivity="CONFIDENTIAL",
        required_quality=95.0
    )
    res = global_pipeline.execute(req)

    assert res.success is True
    assert res.final_model.lower() == "advanced"
    assert res.quality_score >= 95.0
    assert res.copilot_explanation is not None
    assert "WHY ADVANCED?" in res.copilot_explanation


def test_5_scenario_3_semantic_cache_cross_phrasing():
    """
    SCENARIO 3: Semantic Cache
    Call 1: 'Explain cloud computing in simple terms.' -> Cache MISS
    Call 2: 'Can you explain cloud computing simply?' -> Cache HIT
    """
    p1 = "Explain cloud computing in simple terms."
    p2 = "Can you explain cloud computing simply?"

    # Request 1: Cache Miss
    r1 = global_pipeline.execute(ChatRequest(prompt=p1, use_cache=True))
    assert r1.cache_hit is False
    assert r1.cost > 0.0

    # Request 2: Semantic Cache Hit
    r2 = global_pipeline.execute(ChatRequest(prompt=p2, use_cache=True))
    assert r2.cache_hit is True
    assert r2.cost == 0.0
    assert "cache" in r2.execution_mode.lower()
    assert r2.response == r1.response


def test_6_scenario_4_quality_guardrail_fallback():
    """
    SCENARIO 4: Quality Guardrail
    If model quality < required threshold (e.g. required 95), fallback to Advanced.
    """
    prompt = "Draft an executive policy memo for quarterly infrastructure cost governance."
    req = ChatRequest(
        prompt=prompt,
        required_quality=95.0,
        use_cache=False
    )
    res = global_pipeline.execute(req)

    assert res.success is True
    assert res.final_model.lower() == "advanced"
    assert res.quality_score >= 95.0


def test_7_scenario_5_low_budget_block():
    """
    SCENARIO 5: Low Budget Constraint
    When budget is insufficient to satisfy the required quality, request is blocked
    with clear explanation (Never silently violate budget).
    """
    prompt = "Execute deep mathematical reasoning and fraud risk discovery across multi-cloud ledgers."
    # Custom budget remaining = ₹0.0001 (below any model cost)
    req = ChatRequest(
        prompt=prompt,
        department="Finance",
        required_quality=95.0,
        custom_budget={
            "monthly_budget": 10.0,
            "current_spend": 9.9999,
            "remaining_budget": 0.0001
        },
        use_cache=False
    )
    res = global_pipeline.execute(req)

    assert res.success is False
    assert res.selected_model == "none"
    assert "budget constraints" in res.response.lower()
    assert "cannot satisfy" in res.response.lower()


def test_8_scenario_6_what_if_simulator():
    """
    SCENARIO 6: What-If Model Simulator
    Compare Small vs Medium vs Advanced for enterprise architecture review.
    """
    prompt = "Analyze this enterprise architecture and identify security risks."
    sim = ModelSimulator.simulate(prompt=prompt, required_quality=90.0)

    assert len(sim.comparisons) == 3
    tiers = {c.tier: c for c in sim.comparisons}

    assert tiers["SMALL"].is_valid is False
    assert tiers["MEDIUM"].is_valid is True
    assert tiers["ADVANCED"].is_valid is True

    assert sim.recommended_tier == "MEDIUM"
    assert sim.estimated_savings_vs_advanced > 0


def test_9_scenario_7_baseline_vs_optimized_analytics():
    """
    SCENARIO 7: Baseline vs Optimized & Cost per Successful Outcome
    """
    summary = AnalyticsEngine.get_summary()

    # Core business KPIs
    assert summary.baseline_cost == 1000.0
    assert summary.total_ai_spend == 620.0
    assert summary.total_savings == 380.0
    assert summary.savings_percentage == 38.0
    assert summary.average_quality == 94.2

    # Cost per successful outcome
    # Total AI Spend / Successful Outcomes
    assert summary.cost_per_successful_outcome == 6.20

    # Budget
    assert summary.budget_usage_percent == 62.0
    assert summary.budget_status == "normal"
