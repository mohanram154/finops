import os
from .base import (
    LLMProvider,
    ModelTier,
    ModelMetadata,
    GenerationResponse,
    AnalysisResponse,
    ControlledFailureException
)
from .registry import (
    REGISTERED_MODELS,
    TIER_DEFAULT_MODELS,
    get_registered_models,
    get_model_metadata,
    get_models_by_tier
)
from .simulated import SimulatedLLMProvider
from .real_provider import RealLLMProvider

def get_provider(mode: str = None) -> LLMProvider:
    """
    Factory function returning the active LLM provider.
    Mode resolution priority:
    1. Explicit `mode` parameter ('real', 'simulation', 'real')
    2. Environment variable `APP_MODE`
    3. Default to SimulatedLLMProvider (real Mode)
    """
    app_mode = (mode or os.getenv("APP_MODE", "real")).lower()
    if app_mode == "real":
        return RealLLMProvider()
    return SimulatedLLMProvider()

__all__ = [
    "LLMProvider",
    "SimulatedLLMProvider",
    "RealLLMProvider",
    "ModelTier",
    "ModelMetadata",
    "GenerationResponse",
    "AnalysisResponse",
    "ControlledFailureException",
    "REGISTERED_MODELS",
    "TIER_DEFAULT_MODELS",
    "get_registered_models",
    "get_model_metadata",
    "get_models_by_tier",
    "get_provider"
]

