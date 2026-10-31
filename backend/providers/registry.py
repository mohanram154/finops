from typing import List, Dict, Optional
from .base import ModelMetadata, ModelTier

# ============================================================================
# Registered Multi-Vendor Models with Specification real Values
# ============================================================================
# Specification real Values:
# Small:    cost = 0.01 per 1k, latency = 0.5s, quality = 82
# Medium:   cost = 0.05 per 1k, latency = 1.2s, quality = 91
# Advanced: cost = 0.20 per 1k, latency = 2.8s, quality = 97
# ============================================================================

REGISTERED_MODELS: Dict[str, ModelMetadata] = {
    # ------------------------------------------------------------------------
    # SMALL TIER (cost: $0.01/1k tokens, latency: 0.5s, quality: 82)
    # ------------------------------------------------------------------------
    "gpt-4o-mini": ModelMetadata(
        id="gpt-4o-mini",
        provider="openai",
        display_name="OpenAI GPT-4o Mini",
        tier=ModelTier.SMALL,
        input_cost_per_1k_tokens=0.01,
        output_cost_per_1k_tokens=0.01,
        average_latency=0.5,
        quality_score=82.0,
        context_window=128000,
        privacy_level="enterprise",
        capabilities=["fast-chat", "summarization", "json", "screening"],
        available=True,
        is_simulated=True
    ),
    "claude-3-haiku": ModelMetadata(
        id="claude-3-haiku",
        provider="anthropic",
        display_name="Anthropic Claude 3 Haiku",
        tier=ModelTier.SMALL,
        input_cost_per_1k_tokens=0.01,
        output_cost_per_1k_tokens=0.01,
        average_latency=0.5,
        quality_score=82.0,
        context_window=200000,
        privacy_level="zero-retention",
        capabilities=["fast-chat", "classification", "summarization", "rag"],
        available=True,
        is_simulated=True
    ),
    "gemini-1.5-flash": ModelMetadata(
        id="gemini-1.5-flash",
        provider="google",
        display_name="Google Gemini 1.5 Flash",
        tier=ModelTier.SMALL,
        input_cost_per_1k_tokens=0.01,
        output_cost_per_1k_tokens=0.01,
        average_latency=0.5,
        quality_score=82.0,
        context_window=1000000,
        privacy_level="enterprise",
        capabilities=["high-throughput", "multimodal", "fast-chat", "caching"],
        available=True,
        is_simulated=True
    ),

    # ------------------------------------------------------------------------
    # MEDIUM TIER (cost: $0.05/1k tokens, latency: 1.2s, quality: 91)
    # ------------------------------------------------------------------------
    "gpt-4o": ModelMetadata(
        id="gpt-4o",
        provider="openai",
        display_name="OpenAI GPT-4o Omnimodel",
        tier=ModelTier.MEDIUM,
        input_cost_per_1k_tokens=0.05,
        output_cost_per_1k_tokens=0.05,
        average_latency=1.2,
        quality_score=91.0,
        context_window=128000,
        privacy_level="enterprise",
        capabilities=["code-generation", "complex-reasoning", "vision", "json"],
        available=True,
        is_simulated=True
    ),
    "claude-3-5-sonnet": ModelMetadata(
        id="claude-3-5-sonnet",
        provider="anthropic",
        display_name="Anthropic Claude 3.5 Sonnet",
        tier=ModelTier.MEDIUM,
        input_cost_per_1k_tokens=0.05,
        output_cost_per_1k_tokens=0.05,
        average_latency=1.2,
        quality_score=91.0,
        context_window=200000,
        privacy_level="zero-retention",
        capabilities=["code-architecture", "financial-analysis", "writing", "tool-use"],
        available=True,
        is_simulated=True
    ),
    "gemini-1.5-pro": ModelMetadata(
        id="gemini-1.5-pro",
        provider="google",
        display_name="Google Gemini 1.5 Pro",
        tier=ModelTier.MEDIUM,
        input_cost_per_1k_tokens=0.05,
        output_cost_per_1k_tokens=0.05,
        average_latency=1.2,
        quality_score=91.0,
        context_window=2000000,
        privacy_level="enterprise",
        capabilities=["massive-context", "audio-video", "document-analysis", "code"],
        available=True,
        is_simulated=True
    ),

    # ------------------------------------------------------------------------
    # ADVANCED TIER (cost: $0.20/1k tokens, latency: 2.8s, quality: 97)
    # ------------------------------------------------------------------------
    "o1-preview": ModelMetadata(
        id="o1-preview",
        provider="openai",
        display_name="OpenAI o1 Deep Reasoning",
        tier=ModelTier.ADVANCED,
        input_cost_per_1k_tokens=0.20,
        output_cost_per_1k_tokens=0.20,
        average_latency=2.8,
        quality_score=97.0,
        context_window=128000,
        privacy_level="restricted",
        capabilities=["chain-of-thought", "mathematical-proofs", "system-architecture", "cryptography"],
        available=True,
        is_simulated=True
    ),
    "claude-3-opus": ModelMetadata(
        id="claude-3-opus",
        provider="anthropic",
        display_name="Anthropic Claude 3 Opus",
        tier=ModelTier.ADVANCED,
        input_cost_per_1k_tokens=0.20,
        output_cost_per_1k_tokens=0.20,
        average_latency=2.8,
        quality_score=97.0,
        context_window=200000,
        privacy_level="zero-retention",
        capabilities=["deep-research", "legal-audit", "financial-synthesis", "nuanced-analysis"],
        available=True,
        is_simulated=True
    )
}

# Tier default model mappings
TIER_DEFAULT_MODELS: Dict[ModelTier, str] = {
    ModelTier.SMALL: "gpt-4o-mini",
    ModelTier.MEDIUM: "gpt-4o",
    ModelTier.ADVANCED: "o1-preview"
}

def get_registered_models() -> List[ModelMetadata]:
    """Returns all registered models."""
    return list(REGISTERED_MODELS.values())

def get_model_metadata(model_id: str) -> Optional[ModelMetadata]:
    """Returns metadata for a specific model ID."""
    return REGISTERED_MODELS.get(model_id)

def get_models_by_tier(tier: ModelTier) -> List[ModelMetadata]:
    """Returns all models for a specific tier."""
    return [m for m in REGISTERED_MODELS.values() if m.tier == tier]

