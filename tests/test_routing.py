import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.routing.policy_engine import PolicyEngine
from app.routing.budget_engine import BudgetEngine
from app.routing.router import IntelligentRouter, ModelCandidate, RoutingDecisionResult
from app.routing.copilot import RoutingCopilot
from app.core.analyzer import RequestAnalyzer

@pytest.fixture
def router():
    return IntelligentRouter()

# ============================================================================
# 1. Policy Engine Tests
# ============================================================================
def test_policy_engine_evaluation():
    # Standard engineering policy evaluation
    res = PolicyEngine.evaluate(
        department="engineering",
        required_quality=90.0,
        latency_requirement_ms=1000.0
    )
    assert res.allowed is True
    assert res.constraints.min_quality >= 90.0
    assert res.constraints.max_latency_ms == 1000.0

    # Policy violation: marketing department restricts RESTRICTED data
    res_viol = PolicyEngine.evaluate(
        department="marketing",
        sensitivity="RESTRICTED"
    )
    assert res_viol.allowed is False
    assert len(res_viol.violations) > 0

# ============================================================================
# 2. Budget Engine Tests
# ============================================================================
def test_budget_engine_tracking():
    # Specification example: monthly 1000, current spend 620, remaining 380
    status = BudgetEngine.get_budget_status("finance")
    assert status.monthly_budget == 1000.0
    assert status.current_spend == 620.0
    assert status.remaining_budget == 380.0

    # Check budget for normal cost
    check_ok = BudgetEngine.check_budget("finance", estimated_cost=0.20)
    assert check_ok.can_afford is True

    # Check budget when cost exceeds remaining
    check_fail = BudgetEngine.check_budget("finance", estimated_cost=500.0)
    assert check_fail.can_afford is False
    assert "exceeds remaining budget" in check_fail.message

# ============================================================================
# 3. Test Case 1: Translation (Low complexity -> Cheapest valid model)
# ============================================================================
def test_case_1_translation_cheapest_valid_model(router):
    """
    Test Case 1:
    Prompt: 'Translate this sentence into Tamil.'
    Expected:
    Low complexity.
    Cheapest valid model should normally be selected (Small).
    """
    decision: RoutingDecisionResult = router.route(
        prompt="Translate this sentence into Tamil.",
        department="general"
    )
    assert decision.status == "success"
    assert decision.analysis.complexity.value == "LOW"
    # Small model (quality 88, cost 0.01) is cheapest satisfying quality 82
    assert decision.selected_model == "small"
    assert decision.estimated_cost == 0.01
    assert decision.estimated_quality == 88.0
    assert any("Small is cheaper than" in r for r in decision.selection_reason)

# ============================================================================
# 4. Test Case 2: Summarization (Medium complexity -> Small or Medium)
# ============================================================================
def test_case_2_summarization(router):
    """
    Test Case 2:
    Prompt: 'Summarize this document.'
    Expected:
    Medium or Small depending on analyzed requirements.
    """
    decision: RoutingDecisionResult = router.route(
        prompt="Summarize this document.",
        department="general"
    )
    assert decision.status == "success"
    assert decision.analysis.task_type.value == "summarization"
    # Since required quality for standard summarization is ~91,
    # Small (88) is rejected (88 < 91), Medium (93) is selected!
    assert decision.selected_model in ["small", "medium"]
    assert decision.estimated_cost <= 0.05

# ============================================================================
# 5. Test Case 3: Financial Fraud Analysis (High complexity & Criticality)
# ============================================================================
def test_case_3_financial_fraud_analysis(router):
    """
    Test Case 3:
    Prompt: 'Analyze this financial report and identify possible fraud.'
    Expected:
    High complexity.
    High quality requirement.
    Likely Advanced if other models fail the quality constraint.
    """
    decision: RoutingDecisionResult = router.route(
        prompt="Analyze this financial report and identify possible fraud.",
        department="finance"
    )
    assert decision.status == "success"
    assert decision.analysis.complexity.value == "HIGH"
    # Target quality is 97 for critical financial fraud analysis
    # Small (88) ❌, Medium (93) ❌, Advanced (97) ✅
    assert decision.selected_model == "advanced"
    assert decision.estimated_quality == 97.0
    assert decision.estimated_cost == 0.20

# ============================================================================
# 6. Test Case 4: Required Quality set to 95 -> Advanced Chosen
# ============================================================================
def test_case_4_explicit_quality_95(router):
    """
    Test Case 4:
    Set required quality to 95.
    Small: 88 ❌
    Medium: 93 ❌
    Advanced: 97 ✅
    Expected: Advanced.
    """
    decision: RoutingDecisionResult = router.route(
        prompt="Review system specification.",
        required_quality=95.0,
        department="general"
    )
    assert decision.status == "success"
    assert decision.selected_model == "advanced"
    assert decision.estimated_quality == 97.0

    # Ensure rejection reasons explain why Small and Medium were disqualified
    reasons_text = " ".join(decision.selection_reason)
    assert "Small model quality is only 88" in reasons_text
    assert "Medium model quality is only 93" in reasons_text
    assert "Advanced model quality is 97" in reasons_text

# ============================================================================
# 7. Test Case 5: Budget Too Low
# ============================================================================
def test_case_5a_budget_prefers_cheaper_valid_model(router):
    """
    Test Case 5A:
    Set budget too low for Advanced (₹0.20), but sufficient for Medium (₹0.05)
    with required_quality=90.
    Expected: Router prefers cheaper valid model (Medium).
    """
    decision: RoutingDecisionResult = router.route(
        prompt="General business analysis query.",
        required_quality=90.0,
        department="finance",
        custom_budget={"monthly_budget": 100.0, "current_spend": 99.90}  # Remaining: ₹0.10
    )
    assert decision.status == "success"
    # Small (88) fails quality 90
    # Advanced (0.20) fails remaining budget ₹0.10
    # Medium (quality 93, cost 0.05 <= ₹0.10) is valid and selected!
    assert decision.selected_model == "medium"
    assert decision.estimated_cost == 0.05

def test_case_5b_budget_constraint_failure_no_valid_model(router):
    """
    Test Case 5B:
    Set required_quality=95 (only Advanced qualifies) and budget=0.05
    (insufficient for Advanced at ₹0.20).
    Expected: Clear constraint failure, does not silently violate policy.
    """
    decision: RoutingDecisionResult = router.route(
        prompt="Critical mathematical proof verification.",
        required_quality=95.0,
        department="finance",
        custom_budget={"monthly_budget": 100.0, "current_spend": 99.98}  # Remaining: ₹0.02
    )
    assert decision.status == "constraint_failure"
    assert decision.selected_model is None
    assert any("No model satisfies both quality" in r for r in decision.selection_reason)
    assert "ROUTING CONSTRAINT FAILURE" in decision.copilot_explanation

# ============================================================================
# 8. Routing Copilot Tests
# ============================================================================
def test_routing_copilot_explanation(router):
    """
    Verify Routing Copilot dynamic explanation format matches specification:
    WHY MEDIUM?
    ✓ Required quality: 90
    ✓ Medium quality: 93
    ✓ Small quality: 88, therefore rejected
    ✓ Advanced quality: 97 but costs more
    ✓ Latency requirement satisfied
    ✓ Budget available
    Estimated cost: ₹0.05
    Estimated saving compared with Advanced: ₹0.15
    """
    decision = router.route(
        prompt="Analyze departmental metrics.",
        required_quality=90.0,
        department="general"
    )
    assert decision.status == "success"
    assert decision.selected_model == "medium"

    copilot_text = decision.copilot_explanation
    assert "WHY MEDIUM?" in copilot_text
    assert "Required quality: 90" in copilot_text
    assert "Medium quality: 93" in copilot_text
    assert "Small quality: 88, therefore rejected" in copilot_text
    assert "Advanced quality: 97 but costs more" in copilot_text
    assert "Latency requirement satisfied" in copilot_text
    assert "Budget available" in copilot_text
    assert "Estimated cost:" in copilot_text
    assert "Estimated saving compared with Advanced:" in copilot_text
    assert "₹0.15" in copilot_text or "0.15" in copilot_text

# ============================================================================
# 9. Route Preview API Test
# ============================================================================
def test_route_preview_api():
    """
    Test POST /api/v1/route/preview route handler directly.
    """
    from main import preview_route, RoutePreviewRequest
    req = RoutePreviewRequest(
        prompt="Analyze this financial report for fraud",
        department="finance",
        priority="high",
        sensitivity="high",
        required_quality=95.0,
        latency_requirement="normal"
    )
    res: RoutingDecisionResult = preview_route(req)
    assert res.status == "success"
    assert res.selected_model == "advanced"
    assert res.estimated_quality == 97.0
    assert len(res.selection_reason) > 0
    assert len(res.copilot_explanation) > 0
