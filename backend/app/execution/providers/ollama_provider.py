import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

from .base import BaseModelProvider, ModelExecutionResponse

logger = logging.getLogger("nexus.execution.ollama")

class OllamaProvider(BaseModelProvider):
    """
    Local LLM Provider integrating with Ollama (http://127.0.0.1:11434).
    Autodetects running models and safely reports availability without crashing.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self._cached_available_models: List[str] = []
        self._last_check_time: float = 0.0
        self._cached_is_available: bool = False

    def is_available(self) -> bool:
        """
        Fast health-check probe with 0.2s timeout.
        Returns False if Ollama is stopped or unreachable.
        Caches result for 3 seconds to avoid socket lag.
        """
        now = time.time()
        if now - self._last_check_time < 3.0:
            return self._cached_is_available

        self._last_check_time = now
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", headers={"User-Agent": "Nexus-FinOps"})
            with urllib.request.urlopen(req, timeout=0.2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    self._cached_available_models = [m.get("name", "") for m in data.get("models", [])]
                    self._cached_is_available = True
                    return True
        except Exception:
            self._cached_available_models = []
            self._cached_is_available = False
            return False
        self._cached_is_available = False
        return False

    def get_available_models(self) -> List[str]:
        if self.is_available():
            return self._cached_available_models
        return []

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        return {
            "model_id": model_id,
            "provider": "ollama",
            "is_local": True,
            "available": self.is_available() and any(model_id in m for m in self._cached_available_models)
        }

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
        """
        Executes inference against local Ollama server.
        """
        if not self.is_available():
            return ModelExecutionResponse(
                text="",
                model_id=model_id,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=0.0,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message="Ollama daemon is offline or unreachable.",
                provider_type="ollama"
            )

        start_time = time.perf_counter()
        try:
            payload = json.dumps({
                "model": model_id,
                "prompt": prompt,
                "stream": False
            }).encode()

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode())
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                text = data.get("response", "")
                in_tokens = data.get("prompt_eval_count", len(prompt) // 4)
                out_tokens = data.get("eval_count", len(text) // 4)
                total_tokens = in_tokens + out_tokens

                # Pricing per tier
                rate = 0.01 if tier == "small" else (0.05 if tier == "medium" else 0.20)
                cost = round((total_tokens * rate) / 1000.0, 4)

                return ModelExecutionResponse(
                    text=text,
                    model_id=model_id,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    latency_ms=round(elapsed_ms, 2),
                    quality_score=force_quality or 92.0,
                    cost=cost,
                    success=True,
                    provider_type="ollama"
                )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"Ollama execution failed for {model_id}: {e}")
            return ModelExecutionResponse(
                text="",
                model_id=model_id,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=round(elapsed_ms, 2),
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Ollama execution error: {str(e)}",
                provider_type="ollama"
            )
