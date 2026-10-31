import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class QualityEvaluationResult(BaseModel):
    quality_score: float = Field(..., description="Overall score 0 - 100")
    success: bool = Field(..., description="True if meets required_quality guardrail")
    relevance_score: float
    correctness_score: float
    completeness_score: float
    instruction_following_score: float
    evaluation_method: str = "rule_based"
    explanation: str

class QualityEvaluator:
    """
    Lightweight rule-based Quality Evaluation Layer evaluating 4 dimensions:
    1. Relevance
    2. Correctness
    3. Completeness
    4. Instruction Following
    """

    @classmethod
    def evaluate(
        cls,
        prompt: str,
        response_text: str,
        task_type: str,
        model_quality: float,
        required_quality: float = 80.0
    ) -> QualityEvaluationResult:
        if not response_text or len(response_text.strip()) == 0:
            return QualityEvaluationResult(
                quality_score=0.0,
                success=False,
                relevance_score=0.0,
                correctness_score=0.0,
                completeness_score=0.0,
                instruction_following_score=0.0,
                evaluation_method="rule_based",
                explanation="Response is empty or failed to generate."
            )

        p_lower = prompt.lower()
        r_lower = response_text.lower()

        # Base anchor from model tier
        base_q = float(model_quality)

        # 1. Relevance: Prompt keywords represented in response
        prompt_words = [w for w in re.findall(r"\w+", p_lower) if len(w) > 3]
        matched_words = [w for w in prompt_words if w in r_lower]
        rel_ratio = len(matched_words) / len(prompt_words) if prompt_words else 1.0
        relevance_score = min(100.0, max(base_q - 5.0, base_q + (rel_ratio * 3.0)))

        # 2. Correctness & Quality Baseline from Model
        correctness_score = base_q

        # 3. Completeness: Length and structural markers
        resp_len = len(response_text.split())
        if resp_len < 5:
            completeness_score = min(60.0, base_q - 25.0)
        elif resp_len < 15:
            completeness_score = min(80.0, base_q - 10.0)
        else:
            completeness_score = min(100.0, base_q + 1.0)

        # 4. Instruction Following: Task-specific checks
        instruction_score = base_q
        if "tamil" in p_lower and not any("\u0b80" <= c <= "\u0bff" for c in response_text):
            instruction_score = min(70.0, base_q - 20.0)  # Missed Tamil script
        elif "code" in p_lower and not any(k in response_text for k in ["def ", "struct ", "fn ", "{", "class "]):
            instruction_score = min(75.0, base_q - 15.0)

        # Weighted aggregate score
        final_score = round(
            (correctness_score * 0.40) +
            (relevance_score * 0.25) +
            (completeness_score * 0.20) +
            (instruction_score * 0.15),
            1
        )

        # Guardrail check
        meets_guardrail = final_score >= required_quality
        status_str = "PASSED" if meets_guardrail else "FAILED"
        explanation = (
            f"Quality {status_str}: evaluated score {final_score:.1f} vs required threshold {required_quality:.1f} "
            f"(Relevance: {relevance_score:.0f}, Correctness: {correctness_score:.0f}, "
            f"Completeness: {completeness_score:.0f}, Instruction: {instruction_score:.0f})"
        )

        return QualityEvaluationResult(
            quality_score=final_score,
            success=meets_guardrail,
            relevance_score=round(relevance_score, 1),
            correctness_score=round(correctness_score, 1),
            completeness_score=round(completeness_score, 1),
            instruction_following_score=round(instruction_score, 1),
            evaluation_method="rule_based",
            explanation=explanation
        )
