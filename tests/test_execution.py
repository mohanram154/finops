import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import app, execute_chat, get_cache_stats, clear_cache
from app.execution import (
    global_pipeline,
    global_cache,
    ChatRequest,
    ChatResponse,
    ExecutionPipeline
)
from app.execution.cost_engine import CostEngine
from app.execution.quality_evaluator import QualityEvaluator
from app.execution.providers.simulation_provider import SimulationProvider
from app.execution.providers.ollama_provider import OllamaProvider
from app.routing.budget_engine import BudgetEngine


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure clean cache and budgets before and after each test."""
    global_cache.clear()
    BudgetEngine.reset()
    yield
    global_cache.clear()
    BudgetEngine.reset()


def test_1_simple_request_execution():
    """
    TEST 1: Simple Request
    "Translate this sentence into Tamil."
    Expected:
    - Request analyzer detects simple task
    - Routing engine selects Small model
    - Executed via Ollama or simulation
    - Cost recorded
    - Token counts recorded
    - Quality evaluated
    """
    req = ChatRequest(
        prompt="Translate this sentence into Tamil.",
        use_cache=False
    )
    res: ChatResponse = global_pipeline.execute(req)

    assert res.success is True
    assert res.selected_model.lower() == "small"
    assert res.final_model.lower() == "small"
    assert res.input_tokens > 0
    assert res.output_tokens > 0
    assert res.total_tokens == res.input_tokens + res.output_tokens
    assert res.cost > 0.0
    # Small model rate is ₹0.01 per 1k tokens
    assert res.cost < 0.01  # A short sentence is < 1000 tokens
    assert res.quality_score >= 75.0
    assert res.cache_hit is False
    assert res.fallback_used is False
    assert len(res.response) > 5


def test_2_complex_request_execution():
    """
    TEST 2: Complex Request
    "Analyze this financial report and identify potential fraud."
    Expected:
    - Routing engine selects Medium or Advanced
    - Executed
    - Higher token count
    - Higher cost
    - Higher quality
    """
    req = ChatRequest(
        prompt="Analyze this financial report and identify potential fraud.",
        use_cache=False
    )
    res: ChatResponse = global_pipeline.execute(req)

    assert res.success is True
    assert res.final_model.lower() in ["medium", "advanced"]
    assert res.quality_score >= 85.0
    assert res.cost > 0.0
    assert res.total_tokens > 0
    # Complex response is more elaborate than simple translation
    assert len(res.response) > 20


def test_3_cache_hit_and_speed():
    """
    TEST 3: Cache Test
    Send identical request twice.
    Expected:
    1st request:
    - Cache miss
    - Model executed
    - Cost > 0
    2nd request:
    - Cache hit
    - Model NOT executed
    - Cost = 0
    - Response time faster
    """
    prompt = "What are the core principles of FinOps framework?"

    # Request 1: Cache Miss
    res1 = global_pipeline.execute(ChatRequest(prompt=prompt, use_cache=True))
    assert res1.cache_hit is False
    assert res1.cost > 0.0
    assert res1.total_tokens > 0

    # Request 2: Cache Hit
    res2 = global_pipeline.execute(ChatRequest(prompt=prompt, use_cache=True))
    assert res2.cache_hit is True
    assert res2.cost == 0.0
    assert res2.response == res1.response
    assert "cache" in res2.execution_mode.lower()

    # Cache stats
    stats = global_cache.get_stats()
    assert stats.total_entries >= 1
    assert stats.cache_hits >= 1
    assert stats.cache_saved_cost > 0.0


def test_4_quality_failure_and_fallback():
    """
    TEST 4: Quality Failure & Fallback Test
    Simulate response where:
    quality_score < required_quality
    Expected:
    - Fallback triggered
    - Upgraded model executed
    - Fallback event recorded
    """
    # Request routing to Medium with high required quality (90)
    # Force quality to 86 (< 90), which triggers guardrail fallback to Advanced (quality 97)
    req = ChatRequest(
        prompt="Draft an internal policy memo for quarterly expenditure.",
        required_quality=90.0,
        force_quality=86.0,
        use_cache=False
    )
    res = global_pipeline.execute(req)

    assert res.fallback_used is True
    assert res.fallback_details is not None
    assert res.fallback_details.fallback_model.lower() == "advanced"
    assert res.fallback_details.initial_model.lower() == "medium"
    assert "quality" in res.fallback_details.reason.lower()
    assert res.final_model.lower() == "advanced"
    assert res.quality_score >= 90.0
    assert res.success is True


def test_5_ollama_unavailable_graceful_simulation():
    """
    TEST 5: Ollama Unavailable Test
    Run without Ollama.
    Expected:
    - Graceful fallback to simulation
    - No crash
    - Successful response
    """
    # Ollama is offline or uninstalled locally
    ollama = OllamaProvider()
    assert ollama.is_available() is False

    # Pipeline should automatically detect and run in simulation mode
    pipeline = ExecutionPipeline()
    assert pipeline.get_execution_mode() == "real / SIMULATION"

    req = ChatRequest(
        prompt="Explain cloud unit economics.",
        use_cache=False
    )
    res = pipeline.execute(req)

    assert res.success is True
    assert res.execution_mode == "simulation"
    assert len(res.response) > 0
    assert res.cost > 0.0


def test_6_cost_engine_math():
    """
    TEST 6: Cost Engine Test
    Verify:
    - input tokens
    - output tokens
    - total tokens
    - cost calculation matches model tier
    """
    # Small: ₹0.01 per 1k tokens
    small_calc = CostEngine.calculate(
        model="small",
        tier="small",
        input_tokens=1000,
        output_tokens=500
    )
    assert small_calc.total_tokens == 1500
    assert small_calc.input_cost == 0.01
    assert small_calc.output_cost == 0.005
    assert small_calc.total_cost == 0.015
    assert small_calc.pricing_type == "Simulated Enterprise Pricing"

    # Medium: ₹0.05 per 1k tokens
    med_calc = CostEngine.calculate(
        model="medium",
        tier="medium",
        input_tokens=1000,
        output_tokens=1000
    )
    assert med_calc.total_tokens == 2000
    assert med_calc.input_cost == 0.05
    assert med_calc.output_cost == 0.05
    assert med_calc.total_cost == 0.10

    # Advanced: ₹0.20 per 1k tokens
    adv_calc = CostEngine.calculate(
        model="advanced",
        tier="advanced",
        input_tokens=2000,
        output_tokens=1000
    )
    assert adv_calc.total_tokens == 3000
    assert adv_calc.input_cost == 0.40
    assert adv_calc.output_cost == 0.20
    assert adv_calc.total_cost == 0.60


def test_7_baseline_comparison():
    """
    TEST 7: Baseline Comparison Test
    Verify:
    - baseline cost (Advanced)
    - optimized cost (Selected)
    - savings percentage
    - cost per successful outcome
    """
    # Optimized cost of 0.015 for 1500 tokens (Small tier)
    # Baseline Advanced cost for 1500 tokens at ₹0.20/1k = 1.5 * 0.20 = ₹0.30
    comp = CostEngine.compare_with_baseline(
        optimized_cost=0.015,
        total_tokens=1500,
        successful_requests=1,
        total_requests=1
    )

    assert comp.baseline_model == "advanced"
    assert comp.baseline_cost == 0.30
    assert comp.optimized_cost == 0.015
    assert comp.savings == 0.285
    assert comp.savings_percentage == 95.0
    assert comp.cost_per_successful_outcome == 0.015


def test_8_api_chat_and_cache_endpoints():
    """Verify endpoint functions and FastAPI route registrations."""
    # 1. Clear cache
    c_res = clear_cache()
    assert c_res["status"] == "success"

    # 2. Call chat endpoint function directly
    chat_req = ChatRequest(
        prompt="Hello NEXUS, summarize cloud cost anomaly detection.",
        department="Engineering",
        use_cache=True
    )
    r1 = execute_chat(chat_req, db=None)
    assert r1.success is True
    assert r1.cache_hit is False
    assert r1.cost > 0

    # 3. Call same prompt again -> Cache Hit
    r2 = execute_chat(chat_req, db=None)
    assert r2.cache_hit is True
    assert r2.cost == 0.0

    # 4. Check cache stats
    stats = get_cache_stats()
    assert stats.cache_hits >= 1
    assert stats.total_entries >= 1

    # 5. Check route registrations on FastAPI app
    registered_paths = [getattr(r, "path", None) for r in app.routes]
    assert "/api/v1/chat" in registered_paths
    assert "/api/v1/cache/stats" in registered_paths
    assert "/api/v1/cache/clear" in registered_paths
