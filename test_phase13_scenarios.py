import os
import sys
from dotenv import load_dotenv

# Ensure backend is on sys.path
sys.path.insert(0, "backend")
load_dotenv("backend/.env", override=True)

# Ensure UTF-8 console output for Tamil / Unicode characters on Windows
sys.stdout.reconfigure(encoding="utf-8")

from app.core.analyzer import RequestAnalyzer, TaskType, ComplexityLevel
from app.execution.pipeline import ExecutionPipeline, ChatRequest, ChatResponse
from app.execution.cache import global_cache

def run_tests():
    pipeline = ExecutionPipeline()
    global_cache.clear()
    
    print("=" * 70)
    print("NEXUS AI FINOPS — PHASE 13 REAL MODE & AUTOMATIC ROUTING VALIDATION")
    print("=" * 70)
    print(f"Active Provider: {pipeline.real_provider.get_active_provider_name()}")
    print(f"Execution Mode: {pipeline.get_execution_mode()}")
    print("-" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: Conversational Query
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Conversational Query: 'How are you?'")
    req1 = ChatRequest(prompt="How are you?", use_cache=False)
    res1 = pipeline.execute(req1)
    print(f"  -> Detected Task Type : {res1.analysis.task_type.value}")
    print(f"  -> Complexity         : {res1.analysis.complexity.value}")
    print(f"  -> Selected Model     : {res1.selected_model}")
    print(f"  -> Execution Mode     : {res1.execution_mode}")
    print(f"  -> Tokens (In/Out/Tot): {res1.input_tokens} / {res1.output_tokens} / {res1.total_tokens}")
    print(f"  -> Cost               : ${res1.cost:.6f}")
    print(f"  -> Latency            : {res1.latency_ms:.1f}ms")
    print(f"  -> Success            : {res1.success}")
    print(f"  -> Response Excerpt   : {res1.response[:120]}...")
    assert res1.analysis.task_type == TaskType.CONVERSATION, f"Expected conversation, got {res1.analysis.task_type}"
    assert res1.selected_model == "small", f"Expected small model, got {res1.selected_model}"
    assert not res1.response.startswith("[ NEXUS"), "Should NOT be simulated output!"
    print("  ✓ TEST 1 PASSED")

    # -------------------------------------------------------------------------
    # TEST 2: General QA Query
    # -------------------------------------------------------------------------
    print("\n[TEST 2] General QA: 'Explain what is a linked list in simple terms'")
    req2 = ChatRequest(prompt="Explain what is a linked list in simple terms", use_cache=True)
    res2 = pipeline.execute(req2)
    print(f"  -> Detected Task Type : {res2.analysis.task_type.value}")
    print(f"  -> Complexity         : {res2.analysis.complexity.value}")
    print(f"  -> Selected Model     : {res2.selected_model}")
    print(f"  -> Execution Mode     : {res2.execution_mode}")
    print(f"  -> Tokens (In/Out/Tot): {res2.input_tokens} / {res2.output_tokens} / {res2.total_tokens}")
    print(f"  -> Cost               : ${res2.cost:.6f}")
    print(f"  -> Latency            : {res2.latency_ms:.1f}ms")
    print(f"  -> Response Excerpt   : {res2.response[:140]}...")
    assert res2.analysis.task_type == TaskType.GENERAL_QA, f"Expected general_qa, got {res2.analysis.task_type}"
    assert res2.selected_model == "small", f"Expected small model, got {res2.selected_model}"
    assert not res2.response.startswith("[ NEXUS"), "Should NOT be simulated output!"
    print("  ✓ TEST 2 PASSED")

    # -------------------------------------------------------------------------
    # TEST 3: Translation Query
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Translation: 'Translate \"Good morning\" into Tamil'")
    req3 = ChatRequest(prompt='Translate "Good morning" into Tamil', use_cache=False)
    res3 = pipeline.execute(req3)
    print(f"  -> Detected Task Type : {res3.analysis.task_type.value}")
    print(f"  -> Complexity         : {res3.analysis.complexity.value}")
    print(f"  -> Selected Model     : {res3.selected_model}")
    print(f"  -> Execution Mode     : {res3.execution_mode}")
    print(f"  -> Tokens (In/Out/Tot): {res3.input_tokens} / {res3.output_tokens} / {res3.total_tokens}")
    print(f"  -> Response Excerpt   : {res3.response.strip()}")
    assert res3.analysis.task_type == TaskType.TRANSLATION, f"Expected translation, got {res3.analysis.task_type}"
    assert res3.selected_model == "small", f"Expected small model, got {res3.selected_model}"
    assert "வணக்கம்" in res3.response or "Good morning" in res3.response, "Expected Tamil translation output"
    print("  ✓ TEST 3 PASSED")

    # -------------------------------------------------------------------------
    # TEST 4: Complex Financial Fraud Query
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Financial Fraud Risk: 'Analyze this financial report and identify fraud risks in the balance sheet.'")
    req4 = ChatRequest(
        prompt="Analyze this financial report and identify fraud risks in the balance sheet.",
        use_cache=False
    )
    res4 = pipeline.execute(req4)
    print(f"  -> Detected Task Type : {res4.analysis.task_type.value}")
    print(f"  -> Complexity         : {res4.analysis.complexity.value}")
    print(f"  -> Criticality        : {res4.analysis.business_criticality.value}")
    print(f"  -> Selected Model     : {res4.selected_model}")
    print(f"  -> Execution Mode     : {res4.execution_mode}")
    print(f"  -> Tokens (In/Out/Tot): {res4.input_tokens} / {res4.output_tokens} / {res4.total_tokens}")
    print(f"  -> Response Excerpt   : {res4.response[:140]}...")
    assert res4.analysis.task_type == TaskType.FINANCIAL_ANALYSIS, f"Expected financial_analysis, got {res4.analysis.task_type}"
    assert res4.selected_model == "advanced", f"Expected advanced model, got {res4.selected_model}"
    print("  ✓ TEST 4 PASSED")

    # -------------------------------------------------------------------------
    # TEST 5: Semantic Cache Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Cache Hit on repeated query: 'Explain what is a linked list in simple terms'")
    req5 = ChatRequest(prompt="Explain what is a linked list in simple terms", use_cache=True)
    res5 = pipeline.execute(req5)
    print(f"  -> Cache Hit          : {res5.cache_hit}")
    print(f"  -> Latency            : {res5.latency_ms:.2f}ms")
    print(f"  -> Cost Saved         : ${res2.cost:.6f} (Actual cost: ${res5.cost:.6f})")
    assert res5.cache_hit is True, "Expected semantic cache hit!"
    assert res5.cost == 0.0, "Cached cost should be $0.00"
    print("  ✓ TEST 5 PASSED")

    # -------------------------------------------------------------------------
    # TEST 6: Quality Guardrail & Automatic Fallback Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Automatic Fallback Trigger on Quality Breach")
    req6 = ChatRequest(
        prompt="Explain what is a linked list in simple terms",
        force_quality=80.0,  # Simulated quality score 80.0 < target quality 82.0 triggers guardrail
        use_cache=False
    )
    res6 = pipeline.execute(req6)
    print(f"  -> Initial Model      : {res6.selected_model}")
    print(f"  -> Fallback Used      : {res6.fallback_used}")
    print(f"  -> Final Model        : {res6.final_model}")
    print(f"  -> Quality Score      : {res6.quality_score}")
    print(f"  -> Success            : {res6.success}")
    assert res6.fallback_used is True, "Fallback should be triggered!"
    assert res6.final_model in ["medium", "advanced"], f"Expected upgraded model, got {res6.final_model}"
    print("  ✓ TEST 6 PASSED")

    # -------------------------------------------------------------------------
    # TEST 7: No Provider Error in Real Mode
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Error handling when APP_MODE=real but no API key configured")
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GOOGLE_API_KEY"] = ""
    os.environ["GROQ_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    pipeline.real_provider.reload_keys()
    
    req7 = ChatRequest(prompt="What is recursion?", use_cache=False)
    res7 = pipeline.execute(req7)
    print(f"  -> Success            : {res7.success}")
    print(f"  -> Execution Mode     : {res7.execution_mode}")
    print(f"  -> Error Response     : {res7.response}")
    assert res7.success is False
    assert "REAL mode is enabled but no valid LLM provider is configured" in res7.response
    assert not res7.response.startswith("[ NEXUS"), "Must NEVER silently fake responses!"
    print("  ✓ TEST 7 PASSED")

    # Restore environment keys
    load_dotenv("backend/.env", override=True)
    pipeline.real_provider.reload_keys()

    print("\n" + "=" * 70)
    print("ALL 7 PHASE 13 TEST CASES PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
