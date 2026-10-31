import sys
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from providers.base import ModelTier, ControlledFailureException, GenerationResponse
from providers.registry import (
    get_registered_models,
    get_model_metadata,
    get_models_by_tier,
    REGISTERED_MODELS
)
from providers.simulated import SimulatedLLMProvider
from providers.real_provider import RealLLMProvider
from providers import get_provider

@pytest.fixture
def provider():
    return SimulatedLLMProvider(simulate_real_sleep=False)

def test_1_list_models_and_verify_real_values():
    """
    1. List Models:
       Verify all registered models have the required specification fields
       and exact realnstration values for Small, Medium, and Advanced tiers.
    """
    models = get_registered_models()
    assert len(models) >= 8, f"Expected at least 8 registered models, found {len(models)}"

    # Multi-vendor verification
    providers = set(m.provider for m in models)
    assert {"openai", "anthropic", "google"}.issubset(providers)

    # Check Small Tier specifications
    small_models = get_models_by_tier(ModelTier.SMALL)
    assert len(small_models) >= 2
    for m in small_models:
        assert m.tier == ModelTier.SMALL
        assert m.input_cost_per_1k_tokens == 0.01
        assert m.output_cost_per_1k_tokens == 0.01
        assert m.average_latency == 0.5
        assert m.quality_score == 82.0
        assert m.is_simulated is True
        assert m.available is True
        assert len(m.capabilities) > 0

    # Check Medium Tier specifications
    medium_models = get_models_by_tier(ModelTier.MEDIUM)
    assert len(medium_models) >= 2
    for m in medium_models:
        assert m.tier == ModelTier.MEDIUM
        assert m.input_cost_per_1k_tokens == 0.05
        assert m.output_cost_per_1k_tokens == 0.05
        assert m.average_latency == 1.2
        assert m.quality_score == 91.0
        assert m.is_simulated is True
        assert m.available is True

    # Check Advanced Tier specifications
    advanced_models = get_models_by_tier(ModelTier.ADVANCED)
    assert len(advanced_models) >= 2
    for m in advanced_models:
        assert m.tier == ModelTier.ADVANCED
        assert m.input_cost_per_1k_tokens == 0.20
        assert m.output_cost_per_1k_tokens == 0.20
        assert m.average_latency == 2.8
        assert m.quality_score == 97.0
        assert m.is_simulated is True
        assert m.available is True

def test_2_execute_each_simulated_model(provider):
    """
    2. Execute Each Simulated Model:
       Test execution across Small, Medium, and Advanced tiers.
    """
    prompt = "Synthesize multi-cloud FinOps invoice variance ledger."

    # Execute Small
    res_small = provider.generate(prompt, tier=ModelTier.SMALL)
    assert res_small.success is True
    assert res_small.tier == ModelTier.SMALL
    assert len(res_small.text) > 0
    assert res_small.quality_score == 82.0

    # Execute Medium
    res_med = provider.generate(prompt, tier=ModelTier.MEDIUM)
    assert res_med.success is True
    assert res_med.tier == ModelTier.MEDIUM
    assert len(res_med.text) > 0
    assert res_med.quality_score == 91.0

    # Execute Advanced
    res_adv = provider.generate(prompt, tier=ModelTier.ADVANCED)
    assert res_adv.success is True
    assert res_adv.tier == ModelTier.ADVANCED
    assert len(res_adv.text) > 0
    assert res_adv.quality_score == 97.0

def test_3_verify_token_calculation(provider):
    """
    3. Verify Token Calculation:
       Ensure estimate_tokens accurate calculation and total_tokens = input + output.
    """
    sample_text = "NEXUS AI FINOPS: Autonomous multi-cloud cost intelligence platform."
    tokens = provider.estimate_tokens(sample_text)
    assert tokens > 0
    assert tokens >= len(sample_text.split())

    res = provider.generate("Explain AWS Reserved Instance break-even formulas.", tier=ModelTier.SMALL)
    assert res.input_tokens > 0
    assert res.output_tokens > 0
    assert res.total_tokens == res.input_tokens + res.output_tokens

def test_4_verify_cost_calculation(provider):
    """
    4. Verify Cost Calculation:
       Ensure costs strictly conform to specification:
       Small: $0.01 / 1k tokens
       Medium: $0.05 / 1k tokens
       Advanced: $0.20 / 1k tokens
    """
    fixed_prompt = "Calculate quarterly cloud amortization for Engineering and Finance."
    
    cost_small = provider.generate(fixed_prompt, tier=ModelTier.SMALL).cost
    cost_medium = provider.generate(fixed_prompt, tier=ModelTier.MEDIUM).cost
    cost_adv = provider.generate(fixed_prompt, tier=ModelTier.ADVANCED).cost

    # Validate tier cost scaling
    assert cost_small < cost_medium < cost_adv

    # Validate exact formula for a known token count
    in_tokens = 1000
    out_tokens = 1000
    assert provider.get_cost(in_tokens, out_tokens, "gpt-4o-mini") == 0.020000  # (1k*0.01 + 1k*0.01)/1000
    assert provider.get_cost(in_tokens, out_tokens, "gpt-4o") == 0.100000       # (1k*0.05 + 1k*0.05)/1000
    assert provider.get_cost(in_tokens, out_tokens, "o1-preview") == 0.400000   # (1k*0.20 + 1k*0.20)/1000

def test_5_verify_simulated_latency(provider):
    """
    5. Verify Simulated Latency:
       Confirm average latencies match specification real values:
       Small: 0.5s, Medium: 1.2s, Advanced: 2.8s
    """
    prompt = "Benchmark simulated response latency across tiers."
    
    lat_small = provider.generate(prompt, tier=ModelTier.SMALL).latency
    lat_medium = provider.generate(prompt, tier=ModelTier.MEDIUM).latency
    lat_adv = provider.generate(prompt, tier=ModelTier.ADVANCED).latency

    assert lat_small == 0.5
    assert lat_medium == 1.2
    assert lat_adv == 2.8
    assert lat_small < lat_medium < lat_adv

def test_6_verify_controlled_failure_capability(provider):
    """
    6. Verify Controlled Failure Capability:
       Confirm deterministic fault injection via parameters, keywords, and exceptions.
    """
    # Trigger 1: Explicit parameter simulate_failure=True
    res_param = provider.generate("Standard prompt", simulate_failure=True)
    assert res_param.success is False
    assert res_param.cost == 0.0
    assert res_param.quality_score == 0.0
    assert "CONTROLLED_SIMULATED_FAILURE" in res_param.error_message

    # Trigger 2: Keyword trigger in prompt
    res_kw1 = provider.generate("Process audit log [SIMULATE_FAIL] for tenant-99")
    assert res_kw1.success is False
    assert res_kw1.cost == 0.0

    res_kw2 = provider.generate("Query endpoint with [TIMEOUT] trigger")
    assert res_kw2.success is False

    # Trigger 3: Exception raising mode
    with pytest.raises(ControlledFailureException) as exc_info:
        provider.generate("Test exception", simulate_failure=True, raise_on_failure=True)
    assert "CONTROLLED_SIMULATED_FAILURE" in str(exc_info.value)

def test_provider_factory_and_real_mode_fallback():
    """
    Verify get_provider() factory returns SimulatedLLMProvider in real mode,
    and RealLLMProvider gracefully handles real mode without credentials.
    """
    real_provider = get_provider(mode="real")
    assert isinstance(real_provider, SimulatedLLMProvider)

    real_provider = get_provider(mode="real")
    assert isinstance(real_provider, RealLLMProvider)
    # Without real API keys, real provider gracefully simulates execution
    res = real_provider.generate("Safe fallback prompt in real mode", tier=ModelTier.SMALL)
    assert res.success is True
    assert res.tier == ModelTier.SMALL

