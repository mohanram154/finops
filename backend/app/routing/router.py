import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.analyzer import RequestAnalyzer, AnalysisResult
from .policy_engine import PolicyEngine, PolicyEvaluationResult
from .budget_engine import BudgetEngine, BudgetStatus, BudgetCheckResult
from .copilot import RoutingCopilot

# ============================================================================
# Model Candidate Specification
# ============================================================================
class ModelCandidate(BaseModel):
    id: str
    tier: str  # "small", "medium", "advanced"
    display_name: str
    quality: float
    cost_per_1k: float  # Base cost per 1k tokens
    latency_ms: float
    available: bool = True
    privacy_level: str = "enterprise"  # "enterprise", "zero-retention", "restricted"
    capabilities: List[str] = Field(default_factory=list)

# Specification Configurable Defaults:
# SMALL:    quality: 88, cost: 0.01, latency: 100
# MEDIUM:   quality: 93, cost: 0.05, latency: 200
# ADVANCED: quality: 97, cost: 0.20, latency: 400
DEFAULT_MODELS: List[ModelCandidate] = [
    ModelCandidate(
        id="small",
        tier="small",
        display_name="Small Tier Model (GPT-4o Mini / Gemini Flash)",
        quality=88.0,
        cost_per_1k=0.01,
        latency_ms=100.0,
        available=True,
        privacy_level="enterprise",
        capabilities=["fast-chat", "summarization", "translation", "screening"]
    ),
    ModelCandidate(
        id="medium",
        tier="medium",
        display_name="Medium Tier Model (GPT-4o / Claude 3.5 Sonnet)",
        quality=93.0,
        cost_per_1k=0.05,
        latency_ms=200.0,
        available=True,
        privacy_level="enterprise",
        capabilities=["code-generation", "financial-analysis", "writing", "tool-use"]
    ),
    ModelCandidate(
        id="advanced",
        tier="advanced",
        display_name="Advanced Tier Model (o1 / Claude 3 Opus)",
        quality=97.0,
        cost_per_1k=0.20,
        latency_ms=400.0,
        available=True,
        privacy_level="restricted",
        capabilities=["deep-reasoning", "fraud-detection", "mathematical-proofs"]
    )
]

# ============================================================================
# Routing Response Schemas
# ============================================================================
class AlternativeModel(BaseModel):
    model: str
    cost: float
    quality: float
    latency_ms: float

class RoutingDecisionResult(BaseModel):
    request_id: str
    selected_model: Optional[str] = None
    tier: Optional[str] = None
    selection_reason: List[str]
    estimated_cost: Optional[float] = None
    estimated_latency_ms: Optional[float] = None
    estimated_quality: Optional[float] = None
    historical_task_quality: Optional[float] = None
    historical_success_rate: Optional[float] = None
    alternatives: List[AlternativeModel] = Field(default_factory=list)
    copilot_explanation: str
    status: str = "success"  # "success" or "constraint_failure"
    analysis: Optional[AnalysisResult] = None
    policy: Optional[PolicyEvaluationResult] = None
    budget: Optional[BudgetStatus] = None

# ============================================================================
# Historical Task Stats Lookup from Request Ledger
# ============================================================================
TASK_DB_MAPPING = {
    "translation": ["translation"],
    "coding": ["code_generation", "sql_optimization", "unit_test_creation", "api_design", "bug_triage", "code_review"],
    "financial_analysis": ["financial_statement_audit", "expense_anomaly_detection", "q3_revenue_forecast", "tax_deduction_check"],
    "document_analysis": ["vendor_contract_analysis", "benefits_policy_qa"],
    "summarization": ["performance_review_summary", "resume_screening", "seo_blog_post"],
    "creative_generation": ["ad_campaign_copy", "email_newsletter", "product_launch_pitch"],
    "customer_support": ["customer_sentiment_analysis", "benefits_policy_qa"],
    "classification": ["resume_screening", "bug_triage"],
    "extraction": ["expense_anomaly_detection", "tax_deduction_check"],
    "reasoning": ["financial_statement_audit", "code_review"],
    "conversation": ["customer_sentiment_analysis", "benefits_policy_qa"],
    "general_qa": ["performance_review_summary", "benefits_policy_qa"],
    "data_analysis": ["expense_anomaly_detection", "q3_revenue_forecast"]
}

def get_historical_task_stats(task_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Fetches real historical performance metrics from SQLite RequestRecord
    for the specific task category.
    """
    subtasks = TASK_DB_MAPPING.get(task_type.lower(), [task_type.lower()])
    stats = {}
    try:
        from database.connection import SessionLocal
        from database.models import RequestRecord
        db = SessionLocal()
        try:
            records = db.query(
                RequestRecord.selected_model,
                RequestRecord.quality_score,
                RequestRecord.success,
                RequestRecord.latency
            ).filter(RequestRecord.task_type.in_(subtasks)).all()

            def get_tier(m_name: str) -> str:
                m_low = (m_name or "").lower()
                if any(k in m_low for k in ["mini", "flash", "haiku", "small"]):
                    return "small"
                if any(k in m_low for k in ["opus", "o1", "advanced"]):
                    return "advanced"
                return "medium"

            by_tier = {}
            for r in records:
                tier = get_tier(r[0])
                if tier not in by_tier:
                    by_tier[tier] = {"count": 0, "q_sum": 0.0, "succ": 0, "lat_sum": 0.0}
                by_tier[tier]["count"] += 1
                by_tier[tier]["q_sum"] += (r[1] * 100.0 if r[1] <= 1.0 else r[1])
                by_tier[tier]["succ"] += (1 if r[2] else 0)
                by_tier[tier]["lat_sum"] += (r[3] or 0.0)

            for tier, d in by_tier.items():
                if d["count"] > 0:
                    stats[tier] = {
                        "count": d["count"],
                        "avg_quality": round(d["q_sum"] / d["count"], 1),
                        "success_rate": round((d["succ"] / d["count"]) * 100.0, 1),
                        "avg_latency": round(d["lat_sum"] / d["count"], 1)
                    }
        finally:
            db.close()
    except Exception:
        pass
    return stats

# ============================================================================
# Intelligent Routing Engine
# ============================================================================
class IntelligentRouter:
    """
    Intelligent LLM Router implementing the 8-step routing algorithm.
    Optimizes for lowest financial cost while strictly satisfying quality,
    latency, governance policies, and remaining budget limits.
    """

    def __init__(self, models: Optional[List[ModelCandidate]] = None):
        self.models = [m.model_copy() for m in (models or DEFAULT_MODELS)]

    def route(
        self,
        prompt: str,
        department: str = "general",
        priority: Optional[str] = None,
        sensitivity: Optional[str] = None,
        required_quality: Optional[float] = None,
        latency_requirement: Optional[str] = None,
        custom_policy: Optional[Dict[str, Any]] = None,
        custom_budget: Optional[Dict[str, float]] = None,
        context: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> RoutingDecisionResult:
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        reasons: List[str] = []
        rejected_models: List[Dict[str, Any]] = []

        # ====================================================================
        # STEP 1: Get Analyzed Request (Module 3 Request Analyzer)
        # ====================================================================
        analysis: AnalysisResult = RequestAnalyzer.analyze(prompt, context)
        
        # Merge explicit caller overrides if provided
        effective_quality = required_quality if required_quality is not None else analysis.required_quality
        effective_sensitivity = sensitivity if sensitivity is not None else analysis.sensitivity.value
        effective_criticality = analysis.business_criticality.value

        # Calculate latency constraint in ms
        max_latency_ms: Optional[float] = None
        if latency_requirement:
            lat_str = latency_requirement.lower()
            if "realtime" in lat_str or "500" in lat_str or lat_str == "low":
                max_latency_ms = 500.0
            elif "normal" in lat_str or "interactive" in lat_str:
                max_latency_ms = 1500.0
            elif "deep" in lat_str or "batch" in lat_str:
                max_latency_ms = 5000.0
        elif "500ms" in analysis.latency_requirement:
            max_latency_ms = 500.0
        elif "1500ms" in analysis.latency_requirement:
            max_latency_ms = 1500.0

        # ====================================================================
        # STEP 2: Get Applicable Policy
        # ====================================================================
        policy_eval = PolicyEngine.evaluate(
            department=department,
            required_quality=effective_quality,
            latency_requirement_ms=max_latency_ms,
            sensitivity=effective_sensitivity,
            business_criticality=effective_criticality,
            custom_policy=custom_policy
        )

        if not policy_eval.allowed:
            fail_reason = [f"Policy Violation: {v}" for v in policy_eval.violations]
            return RoutingDecisionResult(
                request_id=req_id,
                selected_model=None,
                tier=None,
                selection_reason=fail_reason,
                copilot_explanation=f"ROUTING BLOCKED BY POLICY:\n" + "\n".join(fail_reason),
                status="constraint_failure",
                analysis=analysis,
                policy=policy_eval
            )

        policy_min_quality = policy_eval.constraints.min_quality
        policy_allowed_models = [m.lower() for m in policy_eval.constraints.allowed_models]

        # Check dynamic FinOps Advisor applied policies (Scenario 7)
        try:
            from app.finops.advisor import FinOpsAdvisor
            if FinOpsAdvisor.is_policy_active("translation_model_cap") and analysis.task_type.value == "translation":
                policy_allowed_models = ["small"]
                reasons.append("FinOps Advisor Policy Applied: Eligible translation requests capped at Small tier.")
            elif FinOpsAdvisor.is_policy_active("low_priority_model_cap") and analysis.priority.value in ["low", "normal"] and effective_quality <= 90:
                policy_allowed_models = [m for m in policy_allowed_models if m != "advanced"]
                reasons.append("FinOps Advisor Policy Applied: Low-priority requests capped at Medium tier.")
        except Exception:
            pass

        # Target required quality is at least the policy's required quality
        target_quality = max(effective_quality, policy_min_quality)
        reasons.append(f"Required quality is {int(target_quality) if target_quality.is_integer() else target_quality}")

        # Total tokens for cost calculation
        total_tokens = analysis.estimated_input_tokens + analysis.estimated_output_tokens
        # Normalize total tokens to 1k unit for standard per-request baseline if short
        calc_tokens = max(total_tokens, 1000)

        # Retrieve budget status
        budget_status = BudgetEngine.get_budget_status(department, custom_budget)
        remaining_budget = budget_status.remaining_budget

        # Historical task performance lookup from database ledger
        hist_stats = get_historical_task_stats(analysis.task_type.value)

        # ====================================================================
        # STEP 3 - 7: Filter Model Candidates
        # ====================================================================
        valid_candidates: List[Dict[str, Any]] = []

        for m in self.models:
            m_id = m.id.lower()
            m_tier = m.tier.lower()

            hist_info = hist_stats.get(m_tier, {})
            hist_quality = hist_info.get("avg_quality")
            hist_success = hist_info.get("success_rate", 98.0)
            hist_latency = hist_info.get("avg_latency", m.latency_ms)
            effective_m_quality = round(0.6 * m.quality + 0.4 * hist_quality, 1) if hist_quality is not None else m.quality

            # STEP 3: Filter models that are unavailable
            if not m.available:
                rejected_models.append({"model": m.id, "quality": m.quality, "reason": "Model currently unavailable"})
                continue

            # Check Policy Allowed Models
            if policy_allowed_models and m_id not in policy_allowed_models and m_tier not in policy_allowed_models:
                rejected_models.append({"model": m.id, "quality": m.quality, "reason": f"Model not permitted by {department} policy"})
                continue

            # STEP 4: Remove models that do not meet minimum quality
            if m.quality < target_quality:
                reasons.append(f"{m.display_name.split()[0]} model quality is only {int(m.quality) if m.quality.is_integer() else m.quality}")
                rejected_models.append({
                    "model": m.id,
                    "quality": m.quality,
                    "reason": f"Quality {m.quality} < required {target_quality}"
                })
                continue

            # STEP 5: Remove models that violate latency requirements
            if policy_eval.constraints.max_latency_ms and m.latency_ms > policy_eval.constraints.max_latency_ms:
                rejected_models.append({
                    "model": m.id,
                    "quality": m.quality,
                    "reason": f"Latency {m.latency_ms}ms > max {policy_eval.constraints.max_latency_ms}ms"
                })
                continue

            # STEP 6: Remove models that violate privacy / sensitivity requirements
            if effective_sensitivity in ["CONFIDENTIAL", "RESTRICTED"] and m.privacy_level == "public":
                rejected_models.append({
                    "model": m.id,
                    "quality": m.quality,
                    "reason": f"Public model cannot process {effective_sensitivity} data"
                })
                continue

            # STEP 7: Check budget
            # Calculate cost: cost_per_1k * (calc_tokens / 1000)
            model_cost = round((calc_tokens * m.cost_per_1k) / 1000.0, 4)
            if model_cost > remaining_budget:
                rejected_models.append({
                    "model": m.id,
                    "quality": m.quality,
                    "cost": model_cost,
                    "reason": f"Estimated cost ₹{model_cost:.2f} exceeds remaining budget ₹{remaining_budget:.2f}"
                })
                continue

            # Model passed all constraints!
            valid_candidates.append({
                "model": m,
                "cost": model_cost,
                "quality": m.quality,
                "effective_quality": effective_m_quality,
                "success_rate": hist_success,
                "latency_ms": m.latency_ms,
                "historical_quality": hist_quality,
                "historical_latency": hist_latency
            })

        # ====================================================================
        # Handle Constraint Failure (No valid model)
        # ====================================================================
        if not valid_candidates:
            fail_reasons = [f"No model satisfies both quality ({target_quality}) and budget (₹{remaining_budget:.2f})."]
            for r in rejected_models:
                fail_reasons.append(f"Rejected {r['model']}: {r['reason']}")

            copilot_fail = RoutingCopilot.generate_failure_explanation(
                required_quality=target_quality,
                rejected_models=rejected_models,
                remaining_budget=remaining_budget
            )

            return RoutingDecisionResult(
                request_id=req_id,
                selected_model=None,
                tier=None,
                selection_reason=fail_reasons,
                copilot_explanation=copilot_fail,
                status="constraint_failure",
                analysis=analysis,
                policy=policy_eval,
                budget=budget_status
            )

        # ====================================================================
        # STEP 8: Among remaining valid models, select LOWEST COST model
        # with multi-factor tie-breaking (quality, success rate, latency)
        # ====================================================================
        valid_candidates.sort(key=lambda x: (
            x["cost"],
            -x["quality"],
            -x.get("success_rate", 98.0),
            x["latency_ms"]
        ))

        chosen = valid_candidates[0]
        selected_m = chosen["model"]
        selected_cost = chosen["cost"]

        reasons.append(f"{selected_m.display_name.split()[0]} model quality is {int(selected_m.quality) if selected_m.quality.is_integer() else selected_m.quality}")

        if chosen.get("historical_quality") is not None:
            reasons.append(
                f"Historical task benchmark: {selected_m.tier.capitalize()} averages {chosen['historical_quality']}% quality and {chosen.get('success_rate', 98)}% success on {analysis.task_type.value}"
            )

        # Build alternatives list
        alternatives = []
        for alt in valid_candidates[1:]:
            alt_m = alt["model"]
            alternatives.append(AlternativeModel(
                model=alt_m.id,
                cost=alt["cost"],
                quality=alt["quality"],
                latency_ms=alt["latency_ms"]
            ))
            reasons.append(f"{selected_m.id.capitalize()} is cheaper than {alt_m.id.capitalize()}")

        reasons.append("Latency requirement is satisfied")
        reasons.append("Budget is available")

        # Generate dynamic Routing Copilot explanation
        copilot_exp = RoutingCopilot.generate_explanation(
            selected_model=selected_m.id,
            selected_quality=selected_m.quality,
            selected_cost=selected_cost,
            selected_latency_ms=selected_m.latency_ms,
            required_quality=target_quality,
            reasons=reasons,
            rejected_models=rejected_models,
            alternatives=[a.model_dump() for a in alternatives],
            budget_remaining=remaining_budget,
            historical_quality=chosen.get("historical_quality"),
            historical_success_rate=chosen.get("success_rate")
        )

        return RoutingDecisionResult(
            request_id=req_id,
            selected_model=selected_m.id,
            tier=selected_m.tier.upper(),
            selection_reason=reasons,
            estimated_cost=selected_cost,
            estimated_latency_ms=selected_m.latency_ms,
            estimated_quality=selected_m.quality,
            historical_task_quality=chosen.get("historical_quality"),
            historical_success_rate=chosen.get("success_rate"),
            alternatives=alternatives,
            copilot_explanation=copilot_exp,
            status="success",
            analysis=analysis,
            policy=policy_eval,
            budget=budget_status
        )

