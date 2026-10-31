import re
import time
import uuid
from typing import Optional, Dict, Any, List
from .base import (
    LLMProvider,
    ModelTier,
    ModelMetadata,
    GenerationResponse,
    AnalysisResponse,
    ControlledFailureException
)
from .registry import REGISTERED_MODELS, TIER_DEFAULT_MODELS, get_model_metadata

class SimulatedLLMProvider(LLMProvider):
    """
    High-fidelity Simulated LLM Provider for NEXUS AI FINOPS real Mode.
    Produces deterministic token counts, exact specification costs, tier-correlated
    latencies, realistic contextual completions, and controlled fault injection.
    """

    def __init__(self, simulate_real_sleep: bool = False):
        self.simulate_real_sleep = simulate_real_sleep
        self.usage_records: List[Dict[str, Any]] = []

    def estimate_tokens(self, text: str) -> int:
        """
        Accurate token estimation heuristic:
        1 token ≈ 4 characters or ~0.75 words, plus overhead for punctuation/code symbols.
        """
        if not text:
            return 0
        words = text.split()
        special_chars = len(re.findall(r"[{}\[\](),;:+\-*\/=<>_\"']", text))
        estimated = int((len(words) * 1.33) + (special_chars * 0.4))
        return max(1, estimated)

    def get_cost(self, input_tokens: int, output_tokens: int, model_id: str) -> float:
        """
        Calculates cost using the model's specification pricing:
        Small:    $0.01 / 1k tokens
        Medium:   $0.05 / 1k tokens
        Advanced: $0.20 / 1k tokens
        """
        meta = get_model_metadata(model_id)
        if not meta:
            # Default to Small tier pricing ($0.01 per 1k)
            in_rate, out_rate = 0.01, 0.01
        else:
            in_rate = meta.input_cost_per_1k_tokens
            out_rate = meta.output_cost_per_1k_tokens

        cost = ((input_tokens * in_rate) + (output_tokens * out_rate)) / 1000.0
        return round(cost, 6)

    def analyze(self, prompt: str, **kwargs) -> AnalysisResponse:
        """
        Semantic analyzer recommending the most cost-effective model tier.
        """
        input_tokens = self.estimate_tokens(prompt)
        prompt_lower = prompt.lower()

        # Task type detection
        if any(w in prompt_lower for w in ["code", "function", "bug", "python", "typescript", "sql", "api", "refactor"]):
            task_type = "code_engineering"
        elif any(w in prompt_lower for w in ["audit", "reconcile", "financial", "revenue", "invoice", "balance", "tax"]):
            task_type = "financial_audit"
        elif any(w in prompt_lower for w in ["summary", "summarize", "tldr", "digest"]):
            task_type = "summarization"
        elif any(w in prompt_lower for w in ["resume", "interview", "candidate", "job"]):
            task_type = "hr_evaluation"
        elif any(w in prompt_lower for w in ["ad", "copy", "newsletter", "campaign", "marketing"]):
            task_type = "marketing_copy"
        else:
            task_type = "general_query"

        # Complexity determination
        if input_tokens > 2500 or any(w in prompt_lower for w in ["complex", "architecture", "monte carlo", "deep reasoning", "formal proof"]):
            complexity = "high"
            recommended_tier = ModelTier.ADVANCED
        elif input_tokens > 800 or any(w in prompt_lower for w in ["review", "optimize", "analyze", "reconcile"]):
            complexity = "medium"
            recommended_tier = ModelTier.MEDIUM
        else:
            complexity = "low"
            recommended_tier = ModelTier.SMALL

        # Suggest models within the recommended tier
        suggested = [m.id for m in REGISTERED_MODELS.values() if m.tier == recommended_tier]

        # Estimate expected cost across all tiers assuming typical 350 output tokens
        sample_output = 350
        cost_by_tier = {
            "SMALL": self.get_cost(input_tokens, sample_output, "gpt-4o-mini"),
            "MEDIUM": self.get_cost(input_tokens, sample_output, "gpt-4o"),
            "ADVANCED": self.get_cost(input_tokens, sample_output, "o1-preview")
        }

        return AnalysisResponse(
            prompt=prompt[:120] + "..." if len(prompt) > 120 else prompt,
            estimated_input_tokens=input_tokens,
            task_type=task_type,
            detected_complexity=complexity,
            recommended_tier=recommended_tier,
            suggested_models=suggested,
            estimated_cost_by_tier=cost_by_tier
        )

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        simulate_failure: bool = False,
        raise_on_failure: bool = False,
        **kwargs
    ) -> GenerationResponse:
        """
        Executes simulated LLM generation with exact specification metrics.
        """
        # Resolve target model metadata
        if model_id and model_id in REGISTERED_MODELS:
            meta = REGISTERED_MODELS[model_id]
        elif tier and tier in TIER_DEFAULT_MODELS:
            meta = REGISTERED_MODELS[TIER_DEFAULT_MODELS[tier]]
        else:
            meta = REGISTERED_MODELS["gpt-4o-mini"]

        # --------------------------------------------------------------------
        # Deterministic Controlled Failure Check
        # --------------------------------------------------------------------
        failure_triggers = ["[SIMULATE_FAIL]", "[TRIGGER_FAILURE]", "[FAIL]", "[ERROR]", "[TIMEOUT]"]
        should_fail = (
            simulate_failure or
            any(trigger in prompt for trigger in failure_triggers) or
            kwargs.get("fail", False)
        )

        if should_fail:
            error_reason = kwargs.get(
                "failure_reason",
                "[CONTROLLED_SIMULATED_FAILURE] 504 Gateway Timeout: Upstream LLM provider saturated."
            )
            if raise_on_failure:
                raise ControlledFailureException(error_reason)

            fail_response = GenerationResponse(
                text="",
                model_id=meta.id,
                provider=meta.provider,
                tier=meta.tier,
                input_tokens=self.estimate_tokens(prompt),
                output_tokens=0,
                total_tokens=self.estimate_tokens(prompt),
                latency=meta.average_latency * 1.5,
                cost=0.0,
                quality_score=0.0,
                success=False,
                error_message=error_reason,
                is_simulated=True
            )
            self._record_usage(fail_response)
            return fail_response

        # --------------------------------------------------------------------
        # Successful Simulated Generation
        # --------------------------------------------------------------------
        input_tokens = self.estimate_tokens(prompt)

        # Context-aware synthetic response text
        response_text = self._build_synthetic_response(prompt, meta)
        output_tokens = self.estimate_tokens(response_text)
        total_tokens = input_tokens + output_tokens

        # Specification Cost Calculation
        cost = self.get_cost(input_tokens, output_tokens, meta.id)

        # Simulated Latency matching specification
        latency = meta.average_latency

        # Optional real sleep if specifically requested (capped at 0.1s in unit tests)
        if self.simulate_real_sleep:
            time.sleep(min(0.05, latency))

        # Specification Quality Score: Small: 82, Medium: 91, Advanced: 97
        quality_score = meta.quality_score

        result = GenerationResponse(
            text=response_text,
            model_id=meta.id,
            provider=meta.provider,
            tier=meta.tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency=latency,
            cost=cost,
            quality_score=quality_score,
            success=True,
            error_message=None,
            is_simulated=True
        )

        self._record_usage(result)
        return result

    def get_usage(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns accumulated simulation metrics.
        """
        total_requests = len(self.usage_records)
        total_tokens = sum(r["total_tokens"] for r in self.usage_records)
        total_spend = sum(r["cost"] for r in self.usage_records)
        failures = sum(1 for r in self.usage_records if not r["success"])

        tier_counts = {
            ModelTier.SMALL.value: sum(1 for r in self.usage_records if r["tier"] == ModelTier.SMALL.value),
            ModelTier.MEDIUM.value: sum(1 for r in self.usage_records if r["tier"] == ModelTier.MEDIUM.value),
            ModelTier.ADVANCED.value: sum(1 for r in self.usage_records if r["tier"] == ModelTier.ADVANCED.value)
        }

        return {
            "total_requests": total_requests,
            "successful_requests": total_requests - failures,
            "failed_requests": failures,
            "total_tokens": total_tokens,
            "total_spend_usd": round(total_spend, 6),
            "tier_distribution": tier_counts
        }

    def _record_usage(self, response: GenerationResponse) -> None:
        self.usage_records.append({
            "model_id": response.model_id,
            "tier": response.tier.value if hasattr(response.tier, "value") else str(response.tier),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.total_tokens,
            "cost": response.cost,
            "latency": response.latency,
            "success": response.success
        })

    def _build_synthetic_response(self, prompt: str, meta: ModelMetadata) -> str:
        p_lower = prompt.lower()
        if "code" in p_lower or "python" in p_lower:
            return (
                f"# Generated by {meta.display_name} ({meta.tier.value} Tier)\n"
                "def solve_finops_optimization(ledger_records: list) -> dict:\n"
                "    total_cost = sum(r.get('cost', 0.0) for r in ledger_records)\n"
                "    savings_opportunity = total_cost * 0.28\n"
                "    return {'status': 'optimized', 'estimated_savings': savings_opportunity}\n"
            )
        elif "reconcile" in p_lower or "financial" in p_lower or "audit" in p_lower:
            return (
                f"Financial Audit Report generated via {meta.display_name}.\n"
                "- Invoice Reconciliation: 100% matched with general ledger charges.\n"
                "- Variance Detected: $0.00 immaterial drift on multi-cloud billing line items.\n"
                "- Recommendation: Automated credit note applied to vendor invoice."
            )
        else:
            return (
                f"Comprehensive response generated by {meta.display_name} ({meta.tier.value} tier). "
                f"Synthesized analysis for query: '{prompt[:60]}...'. "
                f"Evaluation confidence: {meta.quality_score}% with verified constraints."
            )

