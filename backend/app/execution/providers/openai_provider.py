import os
import time
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from .base import BaseModelProvider, ModelExecutionResponse

logger = logging.getLogger("nexus.execution.openai")

class OpenAIProvider(BaseModelProvider):
    """
    Live OpenAI Provider executing calls against api.openai.com.
    Maps Small -> gpt-4o-mini, Medium -> gpt-4o, Advanced -> gpt-4o / o1-mini.
    Returns ModelExecutionResponse with real completions, token counts, and latency.
    """

    MODEL_MAP = {
        "small": "gpt-4o-mini",
        "medium": "gpt-4o",
        "advanced": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
        "o1-mini": "o1-mini"
    }

    TIER_SPECS = {
        "small": {"cost_per_1k": 0.01, "quality": 92.0},
        "medium": {"cost_per_1k": 0.05, "quality": 95.0},
        "advanced": {"cost_per_1k": 0.20, "quality": 98.0}
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("sk-") and len(self.api_key) > 20)

    def get_available_models(self) -> List[str]:
        return ["gpt-4o-mini", "gpt-4o", "o1-mini", "small", "medium", "advanced"]

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        tier = "small" if "mini" in model_id.lower() or "small" in model_id.lower() else "medium"
        return {
            "model_id": model_id,
            "provider": "openai",
            "tier": tier,
            "is_local": False,
            "available": self.is_available()
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
        tier_key = tier.lower() if tier else "medium"
        spec = self.TIER_SPECS.get(tier_key, self.TIER_SPECS["medium"])
        openai_model = self.MODEL_MAP.get(model_id.lower(), self.MODEL_MAP.get(tier_key, "gpt-4o-mini"))

        if not self.is_available():
            return ModelExecutionResponse(
                text="",
                model_id=model_id,
                tier=tier_key,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=0.0,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message="OPENAI_API_KEY is not configured.",
                provider_type="openai"
            )

        start_time = time.perf_counter()
        try:
            payload = json.dumps({
                "model": openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Nexus-FinOps"
                }
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                res_data = json.loads(resp.read().decode("utf-8"))
                choice = res_data["choices"][0]
                text = choice["message"]["content"]
                usage = res_data.get("usage", {})

                in_tokens = usage.get("prompt_tokens", len(prompt) // 4)
                out_tokens = usage.get("completion_tokens", len(text) // 4)
                total_tokens = usage.get("total_tokens", in_tokens + out_tokens)

                cost = round((total_tokens * spec["cost_per_1k"]) / 1000.0, 4)
                quality = force_quality if force_quality is not None else spec["quality"]

                return ModelExecutionResponse(
                    text=text,
                    model_id=openai_model,
                    tier=tier_key,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    latency_ms=elapsed_ms,
                    quality_score=quality,
                    cost=cost,
                    success=True,
                    provider_type="openai"
                )
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                err_msg = err_body.get("error", {}).get("message", e.reason)
            except Exception:
                err_msg = str(e)
            return ModelExecutionResponse(
                text="",
                model_id=openai_model,
                tier=tier_key,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"OpenAI API Error: {err_msg}",
                provider_type="openai"
            )
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ModelExecutionResponse(
                text="",
                model_id=openai_model,
                tier=tier_key,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Network error calling OpenAI: {str(ex)}",
                provider_type="openai"
            )

