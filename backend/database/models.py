import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    Index,
    JSON
)
from .connection import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

# ============================================================================
# 1. Users
# ============================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    email = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    department = Column(String(64), index=True, nullable=False)  # Engineering, Finance, HR, Marketing
    role = Column(String(32), default="developer")  # admin, developer, analyst, manager
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_users_tenant_dept", "tenant_id", "department"),
    )

# ============================================================================
# 2. Requests (Core Financial & Routing Ledger)
# ============================================================================
class RequestRecord(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False)
    user_id = Column(String(64), index=True, nullable=False)
    department = Column(String(64), index=True, nullable=False)  # Engineering, Finance, HR, Marketing
    prompt = Column(Text, nullable=False)
    task_type = Column(String(64), index=True, nullable=False)  # e.g., code_generation, summarization, analysis
    complexity = Column(String(32), nullable=False, default="medium")  # low, medium, high
    sensitivity = Column(String(32), nullable=False, default="internal")  # public, internal, confidential, restricted
    criticality = Column(String(32), nullable=False, default="medium")  # low, medium, high, mission_critical
    priority = Column(String(32), nullable=False, default="normal")  # low, normal, high, urgent
    selected_model = Column(String(64), index=True, nullable=False)
    provider = Column(String(64), index=True, nullable=False)  # openai, anthropic, google, meta
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost = Column(Float, nullable=False, default=0.0)
    actual_cost = Column(Float, nullable=False, default=0.0)
    latency = Column(Float, nullable=False, default=0.0)  # milliseconds
    quality_score = Column(Float, nullable=False, default=1.0)  # 0.0 - 1.0
    cache_hit = Column(Boolean, index=True, nullable=False, default=False)
    fallback_used = Column(Boolean, index=True, nullable=False, default=False)
    success = Column(Boolean, index=True, nullable=False, default=True)
    routing_reason = Column(String(256), nullable=False, default="cost_minimization")

    __table_args__ = (
        Index("ix_requests_tenant_timestamp", "tenant_id", "timestamp"),
        Index("ix_requests_dept_timestamp", "department", "timestamp"),
        Index("ix_requests_model_timestamp", "selected_model", "timestamp"),
        Index("ix_requests_perf", "cache_hit", "fallback_used", "success"),
    )

# ============================================================================
# 3. Model Registry (Tiers: Small, Medium, Advanced)
# ============================================================================
class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(64), unique=True, index=True, nullable=False)  # e.g. gpt-4o-mini, claude-3-5-sonnet
    model_name = Column(String(128), nullable=False)
    provider = Column(String(64), index=True, nullable=False)  # openai, anthropic, google, meta
    tier = Column(String(32), index=True, nullable=False)  # Small, Medium, Advanced
    context_window = Column(Integer, default=128000)
    cost_per_1k_input = Column(Float, nullable=False)
    cost_per_1k_output = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, default=250.0)
    quality_rating = Column(Float, default=0.90)  # baseline capability score 0.0 - 1.0
    is_active = Column(Boolean, default=True, index=True)
    supports_streaming = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_model_registry_tier_provider", "tier", "provider"),
    )

# ============================================================================
# 4. Model Usage
# ============================================================================
class ModelUsage(Base):
    __tablename__ = "model_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    model_id = Column(String(64), index=True, nullable=False)
    date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    total_requests = Column(Integer, default=0, nullable=False)
    successful_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    total_input_tokens = Column(Integer, default=0, nullable=False)
    total_output_tokens = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("ix_model_usage_lookup", "tenant_id", "model_id", "date"),
    )

# ============================================================================
# 5. Routing Decisions
# ============================================================================
class RoutingDecision(Base):
    __tablename__ = "routing_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    request_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False)
    eligible_models = Column(Text, nullable=True)  # JSON-encoded array of candidate models
    selected_model = Column(String(64), index=True, nullable=False)
    tier_selected = Column(String(32), nullable=False)  # Small, Medium, Advanced
    reason = Column(String(256), nullable=False)
    cost_saving_pct = Column(Float, default=0.0)
    sla_met = Column(Boolean, default=True)

# ============================================================================
# 6. Budgets
# ============================================================================
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    department = Column(String(64), index=True, nullable=False)  # Engineering, Finance, HR, Marketing
    period = Column(String(32), default="monthly")  # monthly, quarterly, annual
    allocated_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0.0, nullable=False)
    warning_threshold = Column(Float, default=0.80)  # 80% warning
    hard_limit = Column(Float, default=1.00)  # 100% hard limit
    status = Column(String(32), default="active")  # active, warning, exceeded
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_budgets_lookup", "tenant_id", "department", "period"),
    )

# ============================================================================
# 7. Policies
# ============================================================================
class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    department = Column(String(64), index=True, nullable=True)  # null applies to all departments
    max_cost_per_request = Column(Float, default=1.0)
    allowed_tiers = Column(String(128), default="Small,Medium,Advanced")
    enforce_cache = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

# ============================================================================
# 8. Cache Entries
# ============================================================================
class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(128), unique=True, index=True, nullable=False)
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    prompt_hash = Column(String(64), index=True, nullable=False)
    task_type = Column(String(64), nullable=False)
    model_id = Column(String(64), nullable=False)
    response_text = Column(Text, nullable=False)
    tokens_saved = Column(Integer, default=0)
    cost_saved = Column(Float, default=0.0)
    hit_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    last_accessed = Column(DateTime, default=get_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_cache_tenant_prompt", "tenant_id", "prompt_hash"),
    )

# ============================================================================
# 9. Quality Evaluations
# ============================================================================
class QualityEvaluation(Base):
    __tablename__ = "quality_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eval_id = Column(String(64), unique=True, index=True, nullable=False, default=generate_uuid)
    request_id = Column(String(64), index=True, nullable=False)
    model_id = Column(String(64), index=True, nullable=False)
    evaluation_type = Column(String(32), default="automated")  # automated, human_review, benchmark
    accuracy_score = Column(Float, default=0.90)  # 0.0 - 1.0
    hallucination_detected = Column(Boolean, default=False)
    latency_satisfaction = Column(Float, default=0.95)
    cost_efficiency_score = Column(Float, default=0.90)
    overall_score = Column(Float, default=0.92)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

# ============================================================================
# 10. Daily Metrics
# ============================================================================
class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), index=True, nullable=False)  # YYYY-MM-DD
    tenant_id = Column(String(64), index=True, nullable=False, default="default-tenant")
    department = Column(String(64), index=True, nullable=False)  # Engineering, Finance, HR, Marketing
    total_requests = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    cache_hits = Column(Integer, default=0, nullable=False)
    cache_hit_rate = Column(Float, default=0.0, nullable=False)
    fallback_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    avg_quality_score = Column(Float, default=0.0, nullable=False)
    tokens_total = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_daily_metrics_lookup", "date", "tenant_id", "department"),
    )
