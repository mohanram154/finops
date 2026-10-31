import sys
from pathlib import Path

# Enable UTF-8 console output for Windows terminals
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.execution import global_pipeline, global_cache, ChatRequest
from app.finops import ModelSimulator, FinOpsAdvisor, AnalyticsEngine
from app.routing.budget_engine import BudgetEngine
from app.routing.router import IntelligentRouter

def main():
    print("=" * 75)
    print("NEXUS AI FINOPS - PHASE 4 COMPREHENSIVE END-TO-END SCENARIO VERIFICATION")
    print("=" * 75)

    # Clean cache, budget, & policies before test
    global_cache.clear()
    FinOpsAdvisor.reset_policies()
    BudgetEngine.reset()

    # ------------------------------------------------------------------------
    # SCENARIO 1: Simple Request
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 1: Simple Translation Request ---")
    p1 = 'Translate this sentence into Tamil: "AI is changing the future of software development."'
    s1_req = ChatRequest(prompt=p1, department="Engineering", required_quality=80.0)
    s1_res = global_pipeline.execute(s1_req)
    print(f"Prompt:         {p1}")
    print(f"Selected Model: {s1_res.selected_model.upper()}")
    print(f"Final Model:    {s1_res.final_model.upper()}")
    print(f"Cost:           INR {s1_res.cost:.4f}")
    print(f"Quality:        {s1_res.quality_score:.1f}%")
    print(f"Tokens:         {s1_res.total_tokens} ({s1_res.input_tokens} in / {s1_res.output_tokens} out)")
    print(f"Latency:        {s1_res.latency_ms:.1f} ms")
    assert s1_res.final_model.lower() == "small", "Scenario 1 should select Small model"
    print("[PASS] Scenario 1 Passed!")

    # ------------------------------------------------------------------------
    # SCENARIO 2: Complex Request
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 2: Complex Financial Risk Analysis ---")
    p2 = "Analyze the financial risk of an enterprise AI system that processes customer data and recommend a secure cost optimization strategy."
    s2_req = ChatRequest(
        prompt=p2,
        department="Finance",
        priority="HIGH",
        sensitivity="CONFIDENTIAL",
        required_quality=95.0
    )
    s2_res = global_pipeline.execute(s2_req)
    print(f"Prompt:         {p2[:60]}...")
    print(f"Selected Model: {s2_res.selected_model.upper()}")
    print(f"Final Model:    {s2_res.final_model.upper()}")
    print(f"Cost:           INR {s2_res.cost:.4f}")
    print(f"Quality:        {s2_res.quality_score:.1f}%")
    print(f"Reasoning:\n{s2_res.copilot_explanation}")
    assert s2_res.final_model.lower() == "advanced", "Scenario 2 should select Advanced model"
    print("[PASS] Scenario 2 Passed!")

    # ------------------------------------------------------------------------
    # SCENARIO 3: Semantic Cache (Cross-Phrasing Similarity)
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 3: Semantic Cache (Cross-Phrasing Similarity) ---")
    p3_a = "Explain cloud computing in simple terms."
    p3_b = "Can you explain cloud computing simply?"

    res3_1 = global_pipeline.execute(ChatRequest(prompt=p3_a, use_cache=True))
    print(f"Call 1 ('{p3_a}') -> Cache Hit: {res3_1.cache_hit} (Cost: INR {res3_1.cost:.4f})")
    assert res3_1.cache_hit is False

    res3_2 = global_pipeline.execute(ChatRequest(prompt=p3_b, use_cache=True))
    print(f"Call 2 ('{p3_b}') -> Cache Hit: {res3_2.cache_hit} (Cost: INR {res3_2.cost:.4f})")
    print(f"Cache Mode:     {res3_2.execution_mode}")
    assert res3_2.cache_hit is True
    assert res3_2.cost == 0.0
    print("[PASS] Scenario 3 Passed!")

    # ------------------------------------------------------------------------
    # SCENARIO 4: Quality Guardrail & Fallback
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 4: Quality Guardrail & Fallback ---")
    p4 = "Draft an executive policy memo for quarterly infrastructure cost governance."
    s4_req = ChatRequest(
        prompt=p4,
        required_quality=95.0,
        use_cache=False
    )
    s4_res = global_pipeline.execute(s4_req)
    print(f"Required Quality: 95.0%")
    print(f"Selected Model:   {s4_res.selected_model.upper()}")
    print(f"Final Model:      {s4_res.final_model.upper()}")
    print(f"Quality Score:    {s4_res.quality_score:.1f}%")
    assert s4_res.final_model.lower() == "advanced"
    print("[PASS] Scenario 4 Passed!")

    # ------------------------------------------------------------------------
    # SCENARIO 5: Low Budget Constraint
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 5: Low Budget Constraint ---")
    p5 = "Execute deep mathematical reasoning and fraud risk discovery across multi-cloud ledgers."
    s5_req = ChatRequest(
        prompt=p5,
        department="Finance",
        required_quality=95.0,
        custom_budget={
            "monthly_budget": 10.0,
            "current_spend": 9.9999,
            "remaining_budget": 0.0001
        },
        use_cache=False
    )
    s5_res = global_pipeline.execute(s5_req)
    print(f"Success:          {s5_res.success}")
    print(f"Selected Model:   {s5_res.selected_model}")
    print(f"Response Message: {s5_res.response}")
    assert s5_res.success is False
    assert s5_res.selected_model == "none"
    assert "budget constraints" in s5_res.response.lower()
    print("[PASS] Scenario 5 Passed (Budget Protected)!")

    # ------------------------------------------------------------------------
    # SCENARIO 6: What-If Model Simulator
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 6: What-If Model Simulator ---")
    p6 = "Analyze this enterprise architecture and identify security risks."
    sim = ModelSimulator.simulate(prompt=p6, required_quality=90.0)
    print(f"Prompt: {p6}")
    print(f"Quality Requirement: {sim.required_quality}%")
    for c in sim.comparisons:
        print(f"  {c.tier:8} | Cost: INR {c.estimated_cost:.4f} | Quality: {c.estimated_quality}% | Latency: {c.estimated_latency_ms}ms | Valid: {c.status_label}")
    print(f"Recommended Tier: {sim.recommended_tier} ({sim.recommendation_reason})")
    print(f"Savings vs Advanced: INR {sim.estimated_savings_vs_advanced:.4f} ({sim.savings_percentage}%)")
    assert sim.recommended_tier == "MEDIUM"
    print("[PASS] Scenario 6 Passed!")

    # ------------------------------------------------------------------------
    # SCENARIO 7: FinOps Advisor Policy Application
    # ------------------------------------------------------------------------
    print("\n--- SCENARIO 7: FinOps Advisor Policy Application ---")
    recs = FinOpsAdvisor.get_recommendations()
    print(f"Total Available Recommendations: {len(recs)}")
    applied = FinOpsAdvisor.apply_recommendation("rec_routing_translation")
    print(f"Applied: {applied.title} (Status: {applied.status})")

    # Now route a translation request
    router = IntelligentRouter()
    r_dec = router.route(
        prompt="Translate this enterprise manual into Tamil for international staff.",
        department="Engineering"
    )
    print(f"Router Selection: {r_dec.selected_model.upper()}")
    print(f"Selection Reason: {r_dec.selection_reason[0]}")
    assert r_dec.selected_model.lower() == "small"
    print("[PASS] Scenario 7 Passed!")

    # ------------------------------------------------------------------------
    # BASELINE VS OPTIMIZED & COST PER SUCCESSFUL OUTCOME
    # ------------------------------------------------------------------------
    print("\n--- BASELINE VS OPTIMIZED & COST PER SUCCESSFUL OUTCOME ---")
    summary = AnalyticsEngine.get_summary()
    print(f"Baseline Spend (All Advanced): INR {summary.baseline_cost:.2f}")
    print(f"Optimized Spend (NEXUS):       INR {summary.total_ai_spend:.2f}")
    print(f"Total Net Savings:             INR {summary.total_savings:.2f} ({summary.savings_percentage}%)")
    print(f"Average Delivered Quality:     {summary.average_quality:.1f}%")
    print(f"Cost / Successful Outcome:     INR {summary.cost_per_successful_outcome:.2f}")
    print(f"Monthly Budget Utilization:    {summary.budget_usage_percent}% (Status: {summary.budget_status.upper()})")

    print("\n" + "=" * 75)
    print("ALL PHASE 4 real SCENARIOS & FINOPS OUTCOMES VERIFIED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    main()
