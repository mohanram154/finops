import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import (
    app,
    get_analytics_summary,
    get_analytics_cost,
    get_analytics_quality,
    get_analytics_routing,
    list_finops_recommendations,
    apply_finops_recommendation,
    simulate_model_tradeoffs
)
from app.finops import (
    FinOpsAdvisor,
    FinOpsRecommendation,
    ModelSimulator,
    SimulateRequest,
    SimulateResponse,
    AnalyticsEngine
)
from app.routing.router import IntelligentRouter


@pytest.fixture(autouse=True)
def clean_finops_state():
    """Ensure clean advisor state before and after each test."""
    FinOpsAdvisor.reset_policies()
    yield
    FinOpsAdvisor.reset_policies()


def test_1_finops_advisor_recommendations():
    """Verify autonomous advisor recommendations format and data model."""
    recs = FinOpsAdvisor.get_recommendations()
    assert len(recs) >= 3

    rec_ids = [r.id for r in recs]
    assert "rec_routing_translation" in rec_ids
    assert "rec_semantic_cache_repeated" in rec_ids
    assert "rec_cap_low_priority_medium" in rec_ids

    for r in recs:
        assert r.id.startswith("rec_")
        assert len(r.title) > 0
        assert r.estimated_savings > 0
        assert r.risk in ["low", "medium", "high"]
        assert r.category in ["routing", "cache", "model", "budget"]
        assert r.status in ["recommended", "applied"]


def test_2_apply_recommendation_and_routing_impact():
    """
    SCENARIO 7: Apply recommendation and verify changed routing behavior.
    When 'rec_routing_translation' is applied, translation requests must
    be capped at Small model tier and indicate the FinOps Advisor policy.
    """
    applied = FinOpsAdvisor.apply_recommendation("rec_routing_translation")
    assert applied is not None
    assert applied.status == "applied"
    assert FinOpsAdvisor.is_policy_active("translation_model_cap") is True

    # Test routing on a translation prompt
    router = IntelligentRouter()
    decision = router.route(
        prompt="Translate this corporate memo into Tamil for the regional branch.",
        department="Engineering"
    )

    assert decision.selected_model.lower() == "small"
    assert decision.tier.lower() == "small"
    assert any("FinOps Advisor" in reason for reason in decision.selection_reason)


def test_3_what_if_model_simulator():
    """
    SCENARIO 4: What-If Model Simulator.
    Compares Small, Medium, Advanced and selects lowest cost valid model.
    """
    # Case A: Quality requirement = 90
    # Small (88) is invalid, Medium (93) is valid, Advanced (97) is valid
    # Recommendation: Medium (lowest cost valid model)
    res: SimulateResponse = ModelSimulator.simulate(
        prompt="Summarize the multi-cloud expenditure and highlight anomalous compute spend.",
        required_quality=90.0
    )

    assert len(res.comparisons) == 3
    tiers = {c.tier: c for c in res.comparisons}

    assert tiers["SMALL"].is_valid is False
    assert tiers["SMALL"].estimated_cost < tiers["MEDIUM"].estimated_cost

    assert tiers["MEDIUM"].is_valid is True
    assert tiers["MEDIUM"].estimated_quality == 93.0

    assert tiers["ADVANCED"].is_valid is True
    assert tiers["ADVANCED"].estimated_cost > tiers["MEDIUM"].estimated_cost

    assert res.recommended_tier == "MEDIUM"
    assert "Medium is the lowest-cost model" in res.recommendation_reason
    assert res.estimated_savings_vs_advanced > 0

    # Case B: Quality requirement = 95
    # Small (88) and Medium (93) invalid -> Advanced (97) selected
    res_high = ModelSimulator.simulate(
        prompt="Execute fraud detection audit on multi-cloud supplier ledger.",
        required_quality=95.0
    )
    assert res_high.recommended_tier == "ADVANCED"


def test_4_baseline_vs_optimized_analytics():
    """
    PART 3: Baseline vs Optimized calculation.
    Baseline: All requests -> Advanced (₹1000)
    Optimized: NEXUS Routing (₹620)
    Savings: 38%
    Quality: 94.2%
    Cost per successful outcome: ₹6.20
    """
    summary = AnalyticsEngine.get_summary()

    assert summary.baseline_cost == 1000.0
    assert summary.total_ai_spend == 620.0
    assert summary.total_savings == 380.0
    assert summary.savings_percentage == 38.0
    assert summary.average_quality == 94.2
    assert summary.baseline_average_quality == 97.0
    assert summary.cost_per_successful_outcome == 6.20
    assert summary.cache_savings == 320.0
    assert summary.total_requests >= 500

    # Budget card
    assert summary.monthly_budget == 1000.0
    assert summary.budget_used == 620.0
    assert summary.budget_remaining == 380.0
    assert summary.budget_usage_percent == 62.0
    assert summary.budget_status == "normal"


def test_5_api_endpoints_and_routes():
    """Verify Phase 3 endpoint execution and FastAPI route registration."""
    # Summary
    s = get_analytics_summary(db=None)
    assert s.total_ai_spend == 620.0

    # Cost over time
    costs = get_analytics_cost(db=None)
    assert len(costs) == 7
    assert costs[0].spend > 0

    # Quality vs cost
    qual = get_analytics_quality(db=None)
    assert len(qual) == 3

    # Routing distribution
    routing = get_analytics_routing(db=None)
    assert "model_distribution" in routing
    assert "department_distribution" in routing

    # Recommendations
    recs = list_finops_recommendations(db=None)
    assert len(recs) >= 3

    # Apply recommendation
    applied = apply_finops_recommendation("rec_cap_low_priority_medium")
    assert applied.status == "applied"

    # Simulate
    sim_res = simulate_model_tradeoffs(SimulateRequest(prompt="Test prompt", required_quality=85.0))
    assert sim_res.recommended_tier in ["SMALL", "MEDIUM", "ADVANCED"]

    # Verify routes registered on app
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/api/v1/analytics/summary" in routes
    assert "/api/v1/analytics/cost" in routes
    assert "/api/v1/analytics/quality" in routes
    assert "/api/v1/analytics/routing" in routes
    assert "/api/v1/finops/recommendations" in routes
    assert "/api/v1/finops/recommendations/{rec_id}/apply" in routes
    assert "/api/v1/simulate" in routes
