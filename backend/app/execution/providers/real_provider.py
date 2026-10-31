import os
import time
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from .base import BaseModelProvider, ModelExecutionResponse

logger = logging.getLogger("nexus.execution.real")

class UniversalRealProvider(BaseModelProvider):
    """
    Live Multi-Provider LLM Engine for NEXUS AI FINOPS.
    Connects to real LLM providers in order of availability:
    1. Google Gemini (GEMINI_API_KEY / GOOGLE_API_KEY) - Free tier available
    2. Groq (GROQ_API_KEY) - Ultra-fast free tier available
    3. OpenAI (OPENAI_API_KEY) - When account has active credits
    4. Ollama (http://127.0.0.1:11434) - Local offline free execution

    Dynamically maps the assigned model tier (Small, Medium, Advanced)
    to the target provider's corresponding models.
    """

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv("backend/.env")
        load_dotenv(".env")
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()

    def reload_keys(self):
        from dotenv import load_dotenv
        load_dotenv("backend/.env")
        load_dotenv(".env")
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()

    def get_active_provider_name(self) -> Optional[str]:
        self.reload_keys()
        if self.gemini_key and len(self.gemini_key) > 10 and not self.gemini_key.startswith("your_"):
            return "gemini"
        if self.groq_key and len(self.groq_key) > 10 and not self.groq_key.startswith("your_"):
            return "groq"
        if self.openai_key and len(self.openai_key) > 20 and not self.openai_key.startswith("your_"):
            return "openai"
        return None

    def is_available(self) -> bool:
        return self.get_active_provider_name() is not None

    def get_available_models(self) -> List[str]:
        p = self.get_active_provider_name()
        if p == "gemini":
            return ["gemini-2.5-flash", "gemini-2.5-pro"]
        elif p == "groq":
            return ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
        elif p == "openai":
            return ["gpt-4o-mini", "gpt-4o"]
        return ["small", "medium", "advanced"]

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        p = self.get_active_provider_name() or "none"
        return {
            "model_id": model_id,
            "provider": p,
            "is_real": True,
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
        p = self.get_active_provider_name()
        tier_key = (tier or "medium").lower()

        if p == "gemini":
            res = self._call_gemini(prompt, tier_key, force_quality)
            if not res.success and ("quota" in (res.error_message or "").lower() or "429" in (res.error_message or "").lower()):
                # Quota exceeded on Gemini free tier: Seamlessly failover to Groq if key configured
                if self.groq_key and len(self.groq_key) > 10:
                    groq_res = self._call_groq(prompt, tier_key, force_quality)
                    if groq_res.success:
                        return groq_res
            return res
        elif p == "groq":
            return self._call_groq(prompt, tier_key, force_quality)
        elif p == "openai":
            return self._call_openai(prompt, tier_key, force_quality)
        else:
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
                error_message="No real LLM API keys configured in backend/.env",
                provider_type="real"
            )

    # ------------------------------------------------------------------------
    # 1. Google Gemini Live API
    # ------------------------------------------------------------------------
    def _call_gemini(self, prompt: str, tier: str, force_quality: Optional[float]) -> ModelExecutionResponse:
        start_time = time.perf_counter()
        configured_model = os.getenv("REAL_MODEL_GEMINI") or os.getenv("GEMINI_MODEL")
        if configured_model:
            model_name = configured_model
        elif tier == "advanced":
            model_name = os.getenv("REAL_MODEL_ADVANCED", "gemini-2.5-flash")
        elif tier == "medium":
            model_name = os.getenv("REAL_MODEL_MEDIUM", "gemini-2.5-flash")
        else:
            model_name = os.getenv("REAL_MODEL_SMALL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3}
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Nexus-FinOps"}
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                usage = res_data.get("usageMetadata", {})

                in_tokens = usage.get("promptTokenCount", len(prompt) // 4)
                out_tokens = usage.get("candidatesTokenCount", len(text) // 4)
                total_tokens = usage.get("totalTokenCount", in_tokens + out_tokens)

                cost_rate = 0.01 if tier == "small" else (0.05 if tier == "medium" else 0.20)
                cost = round((total_tokens * cost_rate) / 1000.0, 4)
                quality = force_quality if force_quality is not None else (88.0 if tier == "small" else (93.0 if tier == "medium" else 97.0))

                return ModelExecutionResponse(
                    text=text.strip(),
                    model_id=model_name,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    latency_ms=elapsed_ms,
                    quality_score=quality,
                    cost=cost,
                    success=True,
                    provider_type=f"gemini ({model_name})"
                )
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                err_msg = err_data.get("error", {}).get("message", e.reason)
            except Exception:
                err_msg = str(e)
            return ModelExecutionResponse(
                text="",
                model_id=model_name,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Gemini API Error: {err_msg}",
                provider_type="gemini"
            )
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ModelExecutionResponse(
                text="",
                model_id=model_name,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Network error calling Gemini: {str(ex)}",
                provider_type="gemini"
            )

    # ------------------------------------------------------------------------
    # 2. Groq Live API (OpenAI-compatible, ultra-fast & free)
    # ------------------------------------------------------------------------
    def _call_groq(self, prompt: str, tier: str, force_quality: Optional[float]) -> ModelExecutionResponse:
        start_time = time.perf_counter()
        configured_groq = os.getenv("REAL_MODEL_GROQ") or os.getenv("GROQ_MODEL")
        if configured_groq:
            model_name = configured_groq
            cost_rate = 0.05
            base_q = 93.0
        elif tier == "advanced":
            model_name = os.getenv("GROQ_MODEL_ADVANCED", "openai/gpt-oss-120b")
            cost_rate = 0.20
            base_q = 97.0
        elif tier == "medium":
            model_name = os.getenv("GROQ_MODEL_MEDIUM", "openai/gpt-oss-20b")
            cost_rate = 0.05
            base_q = 93.0
        else:
            model_name = os.getenv("GROQ_MODEL_SMALL", "openai/gpt-oss-20b")
            cost_rate = 0.01
            base_q = 88.0

        payload = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "Nexus-FinOps"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                usage = res_data.get("usage", {})

                in_tokens = usage.get("prompt_tokens", len(prompt) // 4)
                out_tokens = usage.get("completion_tokens", len(text) // 4)
                total_tokens = usage.get("total_tokens", in_tokens + out_tokens)
                cost = round((total_tokens * cost_rate) / 1000.0, 4)
                quality = force_quality if force_quality is not None else base_q

                return ModelExecutionResponse(
                    text=text.strip(),
                    model_id=model_name,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    latency_ms=elapsed_ms,
                    quality_score=quality,
                    cost=cost,
                    success=True,
                    provider_type=f"groq ({model_name})"
                )
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                err_msg = err_data.get("error", {}).get("message", e.reason)
            except Exception:
                err_msg = str(e)
            return ModelExecutionResponse(
                text="",
                model_id=model_name,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Groq API Error: {err_msg}",
                provider_type="groq"
            )
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ModelExecutionResponse(
                text="",
                model_id=model_name,
                tier=tier,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                total_tokens=len(prompt) // 4,
                latency_ms=elapsed_ms,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=f"Network error calling Groq: {str(ex)}",
                provider_type="groq"
            )

    # ------------------------------------------------------------------------
    # 3. OpenAI Live API
    # ------------------------------------------------------------------------
    def _call_openai(self, prompt: str, tier: str, force_quality: Optional[float]) -> ModelExecutionResponse:
        start_time = time.perf_counter()
        if tier == "small":
            model_name = "gpt-4o-mini"
            cost_rate = 0.01
            base_q = 88.0
        elif tier == "medium":
            model_name = "gpt-4o"
            cost_rate = 0.05
            base_q = 93.0
        else:
            model_name = "gpt-4o"
            cost_rate = 0.20
            base_q = 97.0

        payload = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json",
                "User-Agent": "Nexus-FinOps"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                res_data = json.loads(resp.read().decode("utf-8"))
                text = res_data["choices"][0]["message"]["content"]
                usage = res_data.get("usage", {})

                in_tokens = usage.get("prompt_tokens", len(prompt) // 4)
                out_tokens = usage.get("completion_tokens", len(text) // 4)
                total_tokens = usage.get("total_tokens", in_tokens + out_tokens)
                cost = round((total_tokens * cost_rate) / 1000.0, 4)
                quality = force_quality if force_quality is not None else base_q

                return ModelExecutionResponse(
                    text=text.strip(),
                    model_id=model_name,
                    tier=tier,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    latency_ms=elapsed_ms,
                    quality_score=quality,
                    cost=cost,
                    success=True,
                    provider_type=f"openai ({model_name})"
                )
        except urllib.error.HTTPError as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                err_msg = err_data.get("error", {}).get("message", e.reason)
            except Exception:
                err_msg = str(e)
            return ModelExecutionResponse(
                text="",
                model_id=model_name,
                tier=tier,
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
                model_id=model_name,
                tier=tier,
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

