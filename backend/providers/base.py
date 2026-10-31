from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ============================================================================
# Model Tiers
# ============================================================================
class ModelTier(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    ADVANCED = "ADVANCED"

# ============================================================================
# Model Metadata Specification
# ============================================================================
class ModelMetadata(BaseModel):
    id: str
    provider: str
    display_name: str
    tier: ModelTier
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    average_latency: float  # In seconds
    quality_score: float    # Small: 82, Medium: 91, Advanced: 97
    context_window: int
    privacy_level: str      # e.g., "enterprise", "zero-retention", "public"
    capabilities: List[str]
    available: bool = True
    is_simulated: bool = True
    pricing_notice: str = "Simulated realnstration values per Module 2 specification"

# ============================================================================
# Execution Result Schemas
# ============================================================================
class GenerationResponse(BaseModel):
    text: str
    model_id: str
    provider: str
    tier: ModelTier
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency: float  # In seconds
    cost: float     # In USD
    quality_score: float
    success: bool = True
    error_message: Optional[str] = None
    is_simulated: bool = True

class AnalysisResponse(BaseModel):
    prompt: str
    estimated_input_tokens: int
    task_type: str
    detected_complexity: str
    recommended_tier: ModelTier
    suggested_models: List[str]
    estimated_cost_by_tier: Dict[str, float]

class ControlledFailureException(Exception):
    """Raised when a deterministic controlled failure is simulated."""
    def __init__(self, message: str, code: str = "CONTROLLED_SIMULATED_FAILURE"):
        super().__init__(message)
        self.code = code

# ============================================================================
# LLM Provider Abstract Interface
# ============================================================================
class LLMProvider(ABC):
    """
    Vendor-agnostic LLM Provider Interface.
    Must support: analyze, generate, estimate_tokens, get_usage, get_cost.
    """

    @abstractmethod
    def analyze(self, prompt: str, **kwargs) -> AnalysisResponse:
        """
        Analyze prompt semantics, estimate token requirements,
        and recommend an optimal model tier.
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        simulate_failure: bool = False,
        **kwargs
    ) -> GenerationResponse:
        """
        Execute LLM completion or simulation and return full telemetry
        (tokens, latency, cost, quality, response).
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count accurately for arbitrary text.
        """
        pass

    @abstractmethod
    def get_usage(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve accumulated token and financial usage telemetry.
        """
        pass

    @abstractmethod
    def get_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: str
    ) -> float:
        """
        Calculate total invocation cost based on model pricing matrix.
        """
        pass

