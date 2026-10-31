from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# ============================================================================
# Policy Schemas
# ============================================================================
class PolicyConstraints(BaseModel):
    min_quality: float = 80.0
    max_latency_ms: Optional[float] = None
    max_cost_per_request: Optional[float] = None
    allowed_models: List[str] = Field(default_factory=lambda: ["small", "medium", "advanced"])
    allowed_sensitivities: List[str] = Field(default_factory=lambda: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"])

class PolicyDefinition(BaseModel):
    department: str = "general"
    required_quality: float = 80.0
    max_latency_ms: Optional[float] = None
    max_cost_per_request: Optional[float] = None
    sensitivity_level: str = "CONFIDENTIAL"
    allowed_models: List[str] = Field(default_factory=lambda: ["small", "medium", "advanced"])

class PolicyEvaluationResult(BaseModel):
    allowed: bool
    policy_name: str = "default_enterprise_policy"
    department: str
    constraints: PolicyConstraints
    violations: List[str] = Field(default_factory=list)

# ============================================================================
# Default Departmental Policies
# ============================================================================
DEFAULT_POLICIES: Dict[str, PolicyDefinition] = {
    "engineering": PolicyDefinition(
        department="engineering",
        required_quality=85.0,
        max_latency_ms=3000.0,
        max_cost_per_request=2.50,
        allowed_models=["small", "medium", "advanced", "gpt-4o-mini", "gpt-4o", "o1-preview", "claude-3-5-sonnet", "gemini-1.5-pro"]
    ),
    "finance": PolicyDefinition(
        department="finance",
        required_quality=92.0,
        max_latency_ms=4000.0,
        max_cost_per_request=3.00,
        allowed_models=["medium", "advanced", "gpt-4o", "claude-3-5-sonnet", "o1-preview", "claude-3-opus"]
    ),
    "hr": PolicyDefinition(
        department="hr",
        required_quality=80.0,
        max_latency_ms=1500.0,
        max_cost_per_request=0.50,
        allowed_models=["small", "medium", "gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash"]
    ),
    "marketing": PolicyDefinition(
        department="marketing",
        required_quality=85.0,
        max_latency_ms=2000.0,
        max_cost_per_request=1.20,
        allowed_models=["small", "medium", "advanced", "gpt-4o-mini", "claude-3-5-sonnet", "gemini-1.5-flash"]
    ),
    "general": PolicyDefinition(
        department="general",
        required_quality=80.0,
        max_latency_ms=5000.0,
        max_cost_per_request=5.00,
        allowed_models=["small", "medium", "advanced"]
    )
}

# ============================================================================
# Policy Engine
# ============================================================================
class PolicyEngine:
    """
    Evaluates enterprise governance, privacy, quality thresholds, and model allowlists.
    """

    @classmethod
    def evaluate(
        cls,
        department: str,
        required_quality: Optional[float] = None,
        latency_requirement_ms: Optional[float] = None,
        sensitivity: Optional[str] = None,
        business_criticality: Optional[str] = None,
        custom_policy: Optional[Dict[str, Any]] = None
    ) -> PolicyEvaluationResult:
        dept_key = department.lower().strip() if department else "general"
        base_policy = DEFAULT_POLICIES.get(dept_key, DEFAULT_POLICIES["general"])

        # Merge custom policy overrides if provided
        if custom_policy:
            req_qual = custom_policy.get("required_quality", base_policy.required_quality)
            max_lat = custom_policy.get("max_latency_ms", base_policy.max_latency_ms)
            allowed_mods = custom_policy.get("allowed_models", base_policy.allowed_models)
            max_cost = custom_policy.get("max_cost_per_request", base_policy.max_cost_per_request)
        else:
            req_qual = base_policy.required_quality
            max_lat = base_policy.max_latency_ms
            allowed_mods = base_policy.allowed_models
            max_cost = base_policy.max_cost_per_request

        # Reconcile with incoming request requirements
        effective_min_quality = max(req_qual, required_quality) if required_quality is not None else req_qual
        effective_max_latency = min(max_lat, latency_requirement_ms) if (max_lat and latency_requirement_ms) else (latency_requirement_ms or max_lat)

        violations = []

        # Check sensitivity constraints
        sens_upper = sensitivity.upper() if sensitivity else "PUBLIC"
        if sens_upper == "RESTRICTED" and dept_key == "marketing":
            violations.append("Marketing department policy restricts processing RESTRICTED data classification.")

        # Check criticality vs allowed models
        crit_upper = business_criticality.upper() if business_criticality else "LOW"
        if crit_upper == "CRITICAL" and "advanced" not in [m.lower() for m in allowed_mods] and "medium" not in [m.lower() for m in allowed_mods]:
            violations.append("Business critical tasks must allow at least Medium or Advanced tier models.")

        is_allowed = len(violations) == 0

        constraints = PolicyConstraints(
            min_quality=effective_min_quality,
            max_latency_ms=effective_max_latency,
            max_cost_per_request=max_cost,
            allowed_models=allowed_mods
        )

        return PolicyEvaluationResult(
            allowed=is_allowed,
            policy_name=f"{dept_key}_governance_policy",
            department=dept_key,
            constraints=constraints,
            violations=violations
        )

