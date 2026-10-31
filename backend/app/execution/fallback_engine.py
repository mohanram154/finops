from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FallbackAttempt(BaseModel):
    attempt_number: int
    model_id: str
    tier: str
    failure_type: str  # "execution_failure", "quality_threshold_breach", "unavailable"
    reason: str
    quality_score: Optional[float] = None

class FallbackRecord(BaseModel):
    fallback_triggered: bool = False
    initial_model: str
    fallback_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    reason: Optional[str] = None
    final_model: str
    final_status: str  # "success", "failed", "no_fallback_available"
    attempts: List[FallbackAttempt] = Field(default_factory=list)
    frontend_message: Optional[str] = None

class FallbackEngine:
    """
    Manages automated fallback transitions when primary model execution
    fails or violates enterprise quality thresholds.
    """

    @classmethod
    def resolve_next_model(
        cls,
        current_model_id: str,
        alternatives: List[Dict[str, Any]],
        candidates_pool: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Selects next valid fallback model from routing alternatives or escalates tier.
        """
        # 1. Check routing alternatives first
        for alt in alternatives:
            alt_id = alt.get("model", "")
            if alt_id and alt_id.lower() != current_model_id.lower():
                return alt_id

        # 2. Tier escalation fallback (small -> medium -> advanced)
        c_lower = current_model_id.lower()
        if "small" in c_lower:
            return "medium"
        elif "medium" in c_lower:
            return "advanced"
        return None

    @classmethod
    def build_record(
        cls,
        initial_model: str,
        fallback_model: Optional[str],
        reason: str,
        success: bool,
        attempts: List[FallbackAttempt]
    ) -> FallbackRecord:
        triggered = fallback_model is not None and fallback_model.lower() != initial_model.lower()
        final_model = fallback_model if triggered else initial_model
        final_status = "success" if success else "failed"

        frontend_msg = None
        if triggered:
            frontend_msg = f"Fallback triggered: {initial_model.capitalize()} failed quality threshold. {final_model.capitalize()} selected."

        return FallbackRecord(
            fallback_triggered=triggered,
            initial_model=initial_model,
            fallback_model=fallback_model,
            fallback_reason=reason if triggered else None,
            reason=reason if triggered else None,
            final_model=final_model,
            final_status=final_status,
            attempts=attempts,
            frontend_message=frontend_msg
        )
