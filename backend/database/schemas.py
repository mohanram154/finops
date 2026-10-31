from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# ============================================================================
# Request Schemas
# ============================================================================
class RequestBase(BaseModel):
    tenant_id: str = "default-tenant"
    user_id: str
    department: str  # Engineering, Finance, HR, Marketing
    prompt: str
    task_type: str
    complexity: str = "medium"
    sensitivity: str = "internal"
    criticality: str = "medium"
    priority: str = "normal"
    selected_model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    latency: float = 0.0
    quality_score: float = 1.0
    cache_hit: bool = False
    fallback_used: bool = False
    success: bool = True
    routing_reason: str = "cost_minimization"

class RequestCreate(RequestBase):
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None

class RequestUpdate(BaseModel):
    actual_cost: Optional[float] = None
    latency: Optional[float] = None
    quality_score: Optional[float] = None
    success: Optional[bool] = None
    routing_reason: Optional[str] = None

class RequestResponse(RequestBase):
    id: int
    request_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# User Schemas
# ============================================================================
class UserBase(BaseModel):
    tenant_id: str = "default-tenant"
    email: str
    name: str
    department: str
    role: str = "developer"
    is_active: bool = True

class UserCreate(UserBase):
    user_id: Optional[str] = None

class UserResponse(UserBase):
    id: int
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Model Registry Schemas
# ============================================================================
class ModelRegistryBase(BaseModel):
    model_id: str
    model_name: str
    provider: str
    tier: str  # Small, Medium, Advanced
    context_window: int = 128000
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: float = 250.0
    quality_rating: float = 0.90
    is_active: bool = True
    supports_streaming: bool = True

class ModelRegistryCreate(ModelRegistryBase):
    pass

class ModelRegistryResponse(ModelRegistryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Budget Schemas
# ============================================================================
class BudgetBase(BaseModel):
    tenant_id: str = "default-tenant"
    department: str
    period: str = "monthly"
    allocated_amount: float
    spent_amount: float = 0.0
    warning_threshold: float = 0.80
    hard_limit: float = 1.00
    status: str = "active"

class BudgetCreate(BudgetBase):
    budget_id: Optional[str] = None

class BudgetResponse(BudgetBase):
    id: int
    budget_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Policy Schemas
# ============================================================================
class PolicyBase(BaseModel):
    tenant_id: str = "default-tenant"
    name: str
    description: Optional[str] = None
    department: Optional[str] = None
    max_cost_per_request: float = 1.0
    allowed_tiers: str = "Small,Medium,Advanced"
    enforce_cache: bool = True
    is_active: bool = True

class PolicyCreate(PolicyBase):
    policy_id: Optional[str] = None

class PolicyResponse(PolicyBase):
    id: int
    policy_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ============================================================================
# Daily Metrics Schemas
# ============================================================================
class DailyMetricBase(BaseModel):
    date: str
    tenant_id: str = "default-tenant"
    department: str
    total_requests: int = 0
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_hit_rate: float = 0.0
    fallback_count: int = 0
    error_count: int = 0
    avg_quality_score: float = 0.0
    tokens_total: int = 0

class DailyMetricCreate(DailyMetricBase):
    pass

class DailyMetricResponse(DailyMetricBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

