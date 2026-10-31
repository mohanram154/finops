import re
import time
from typing import List, Dict, Any, Optional

from .base import BaseModelProvider, ModelExecutionResponse

class SimulationProvider(BaseModelProvider):
    """
    Deterministic High-Fidelity Simulation Provider for NEXUS AI FINOPS.
    Returns tier-correlated quality scores, latencies, tokens, and costs.
    Allows injecting controlled quality deficits or execution failures for testing.
    """

    TIER_SPECS = {
        "small": {
            "quality": 88.0,
            "latency_ms": 120.0,
            "cost_per_1k": 0.01,
            "display_name": "Small Model (GPT-4o Mini / Gemini Flash)"
        },
        "medium": {
            "quality": 93.0,
            "latency_ms": 220.0,
            "cost_per_1k": 0.05,
            "display_name": "Medium Model (GPT-4o / Claude 3.5 Sonnet)"
        },
        "advanced": {
            "quality": 97.0,
            "latency_ms": 420.0,
            "cost_per_1k": 0.20,
            "display_name": "Advanced Model (o1 / Claude 3 Opus)"
        }
    }

    def is_available(self) -> bool:
        return True  # Simulation is always available

    def get_available_models(self) -> List[str]:
        return ["small", "medium", "advanced", "gpt-4o-mini", "gpt-4o", "o1-preview"]

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        tier = self._resolve_tier(model_id)
        spec = self.TIER_SPECS[tier]
        return {
            "model_id": model_id,
            "tier": tier,
            "display_name": spec["display_name"],
            "quality": spec["quality"],
            "latency_ms": spec["latency_ms"],
            "cost_per_1k": spec["cost_per_1k"],
            "is_simulated": True
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
        resolved_tier = self._resolve_tier(tier or model_id)
        spec = self.TIER_SPECS[resolved_tier]

        # 1. Deterministic Failure Injection
        fail_triggers = ["[SIMULATE_FAIL]", "[FAIL]", "[ERROR]", "[TIMEOUT]"]
        if simulate_failure or any(t in prompt for t in fail_triggers) or kwargs.get("fail", False):
            return ModelExecutionResponse(
                text="",
                model_id=model_id,
                tier=resolved_tier,
                input_tokens=max(1, len(prompt) // 4),
                output_tokens=0,
                total_tokens=max(1, len(prompt) // 4),
                latency_ms=spec["latency_ms"] * 1.5,
                quality_score=0.0,
                cost=0.0,
                success=False,
                error_message=kwargs.get("failure_reason", f"Execution error in {resolved_tier} model."),
                provider_type="simulation"
            )

        # 2. Token Accounting
        in_tokens = max(1, len(prompt) // 4)
        synthetic_text = self._build_realistic_response(prompt, resolved_tier)
        out_tokens = max(10, len(synthetic_text) // 4)
        total_tokens = in_tokens + out_tokens

        # 3. Cost Calculation (Simulated Enterprise Pricing)
        cost = round((total_tokens * spec["cost_per_1k"]) / 1000.0, 4)

        # 4. Quality Score Resolution (supports test override e.g. forcing Medium to 86)
        if force_quality is not None:
            quality = float(force_quality)
        else:
            quality = spec["quality"]

        # Latency
        latency = spec["latency_ms"]

        return ModelExecutionResponse(
            text=synthetic_text,
            model_id=model_id,
            tier=resolved_tier,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=total_tokens,
            latency_ms=latency,
            quality_score=quality,
            cost=cost,
            success=True,
            provider_type="simulation"
        )

    def _resolve_tier(self, name: str) -> str:
        n = (name or "medium").lower()
        if "small" in n or "mini" in n or "haiku" in n or "flash" in n:
            return "small"
        elif "advanced" in n or "o1" in n or "opus" in n:
            return "advanced"
        return "medium"

    def _build_realistic_response(self, prompt: str, tier: str) -> str:
        p_lower = prompt.lower()
        tier_label = tier.upper()

        if "translate" in p_lower or "translation" in p_lower:
            target_lang = "Target Language"
            sample_trans = "Translation processed with verified linguistic accuracy and high semantic fidelity."
            
            if "tamil" in p_lower:
                target_lang = "Tamil"
                sample_trans = "செயற்கை நுண்ணறிவு மென்பொருள் உருவாக்கத்தின் எதிர்காலத்தை மாற்றுகிறது. (AI is changing the future of software development)."
            elif "spanish" in p_lower:
                target_lang = "Spanish"
                sample_trans = "La inteligencia artificial está transformando el futuro del desarrollo de software de manera integral."
            elif "french" in p_lower:
                target_lang = "French"
                sample_trans = "L'intelligence artificielle transforme l'avenir du développement logiciel avec une grande efficacité."
            elif "german" in p_lower:
                target_lang = "German"
                sample_trans = "Künstliche Intelligenz verändert die Zukunft der Softwareentwicklung nachhaltig und effizient."
            elif "hindi" in p_lower:
                target_lang = "Hindi"
                sample_trans = "आर्टिफिशियल इंटेलिजेंस सॉफ्टवेयर विकास के भविष्य को तेजी से बदल रहा है।"
            elif "japanese" in p_lower:
                target_lang = "Japanese"
                sample_trans = "人工知能はソフトウェア開発の未来を大きく変革しています。"
            elif "chinese" in p_lower:
                target_lang = "Chinese"
                sample_trans = "人工智能正在全面改变软件开发的未来。"
            else:
                for lang in ["italian", "portuguese", "russian", "arabic", "korean", "dutch"]:
                    if lang in p_lower:
                        target_lang = lang.capitalize()
                        sample_trans = f"Verified accurate translation into {target_lang} conforming to enterprise linguistic standards."
                        break
            
            return f"[NEXUS {tier_label} - {target_lang} Translation]\n{sample_trans}"
        elif "fraud" in p_lower or "financial" in p_lower:
            return (
                f"[NEXUS {tier_label} Audit Analysis]\n"
                "- Reconciliation: Verified billing transactions against multi-cloud ledger.\n"
                "- Anomaly Detection: 0.02% drift identified in off-peak data transfer.\n"
                "- Assessment: No structural fraud patterns detected; all invoices matched."
            )
        elif "summarize" in p_lower or "summary" in p_lower:
            return (
                f"[NEXUS {tier_label} Executive Summary]\n"
                "Key findings: Cloud infrastructure costs optimized by 34% through proactive rightsizing and caching."
            )
        elif "code" in p_lower or "rust" in p_lower or "python" in p_lower:
            return (
                f"// NEXUS {tier_label} Verified Solution\n"
                "pub struct DistributedLockManager {\n"
                "    quorum_size: usize,\n"
                "    lease_duration_ms: u64,\n"
                "}\n"
                "impl DistributedLockManager {\n"
                "    pub async fn acquire(&self, resource_id: &str) -> Result<bool, &'static str> {\n"
                "        Ok(true)\n"
                "    }\n"
                "}"
            )
        else:
            return f"[NEXUS {tier_label}] Verified response for prompt: '{prompt[:50]}...'. Output conforms to required quality and enterprise safety constraints."

