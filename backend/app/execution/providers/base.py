from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ModelExecutionResponse(BaseModel):
    text: str
    model_id: str
    tier: str = "medium"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    quality_score: float
    cost: float
    success: bool = True
    error_message: Optional[str] = None
    provider_type: str = "simulation"  # "ollama" or "simulation"

class BaseModelProvider(ABC):
    """
    Abstract Model Execution Provider interface.
    Decoupled from intelligent routing decisions.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model_id: str,
        tier: str = "medium",
        required_quality: Optional[float] = None,
        force_quality: Optional[float] = None,
        simulate_failure: bool = False,
        **kwargs
    ) -> ModelExecutionResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass

