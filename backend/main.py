from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
load_dotenv("backend/.env")
load_dotenv(".env")
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import get_settings
from models import HealthResponse, AppConfigInfo
from database.connection import init_db, get_db, check_connection
from database.repository import DatabaseRepository
from database.schemas import RequestCreate, RequestUpdate, RequestResponse
from providers import (
    get_registered_models,
    get_model_metadata,
    get_provider,
    ModelMetadata,
    GenerationResponse,
    AnalysisResponse,
    ModelTier
)
from app.core.analyzer import RequestAnalyzer, AnalysisResult
from app.routing import (
    IntelligentRouter,
    RoutingDecisionResult,
    ModelCandidate
)
from app.execution import (
    global_pipeline,
    global_cache,
    ChatRequest,
    ChatResponse,
    CacheStats
)
from app.finops import (
    FinOpsAdvisor,
    FinOpsRecommendation,
    ModelSimulator,
    SimulateRequest,
    SimulateResponse,
    AnalyticsEngine,
    AnalyticsSummary,
    CostOverTimePoint,
    QualityVsCostPoint
)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and indexes on application start
    init_db()
    yield

app = FastAPI(
    title="NEXUS AI FINOPS",
    description="Intelligent Multi-Cloud Financial Operations Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    tags=["System"]
)
def get_health() -> HealthResponse:
    """
    Standard health check endpoint required by NEXUS AI FINOPS specification.
    """
    return HealthResponse(
        status="healthy",
        service="nexus-ai-finops"
    )

@app.get(
    "/health",
    summary="Root Health & Capability Status",
    tags=["System"]
)
def get_root_health():
    """
    Returns platform health, execution mode, database connectivity,
    cache status, and registered model count.
    """
    db_conn = check_connection()
    exec_mode = global_pipeline.get_execution_mode().lower()
    return {
        "status": "healthy",
        "service": "nexus-ai-finops",
        "mode": "simulation" if "simulation" in exec_mode or "real" in exec_mode else "ollama",
        "database": db_conn["status"],
        "cache": "available",
        "models": len(get_registered_models()),
        "ollama_available": global_pipeline.ollama.is_available()
    }

@app.get(
    "/api/v1/budget",
    summary="Get Departmental AI Budgets & Spend Status",
    tags=["Budget"]
)
def get_budgets(department: Optional[str] = Query(None, description="Filter by department")):
    """Returns monthly and daily budget tracking for all departments or specified department."""
    from app.routing.budget_engine import BudgetEngine, DEFAULT_DEPARTMENT_BUDGETS
    if department:
        return BudgetEngine.get_budget_status(department)
    return {
        dept: BudgetEngine.get_budget_status(dept)
        for dept in DEFAULT_DEPARTMENT_BUDGETS
    }

@app.get(
    "/api/v1/policies",
    summary="Get Enterprise & Departmental Routing Policies",
    tags=["Policies"]
)
def get_policies(department: Optional[str] = Query(None, description="Filter by department")):
    """Returns active enterprise governance policies and dynamically applied FinOps rules."""
    from app.routing.policy_engine import DEFAULT_POLICIES
    from app.finops.advisor import FinOpsAdvisor
    if department and department.lower() in DEFAULT_POLICIES:
        return {
            "policy": DEFAULT_POLICIES[department.lower()],
            "active_overrides": FinOpsAdvisor.get_applied_policies()
        }
    return {
        "policies": DEFAULT_POLICIES,
        "active_overrides": FinOpsAdvisor.get_applied_policies()
    }

@app.get(
    "/api/v1/system/info",
    response_model=AppConfigInfo,
    summary="System Configuration & Database Status",
    tags=["System"]
)
def get_system_info(db: Optional[Session] = Depends(get_db)) -> AppConfigInfo:
    """
    Returns operating mode, database connectivity, and telemetry metrics.
    """
    db_status = check_connection()
    
    # Handle direct function call without dependency injection
    if db is None or not hasattr(db, "query"):
        from database.connection import SessionLocal
        local_db = SessionLocal()
        try:
            total_requests = DatabaseRepository.count_requests(local_db)
        finally:
            local_db.close()
    else:
        total_requests = DatabaseRepository.count_requests(db)
    
    return AppConfigInfo(
        service="nexus-ai-finops",
        app_mode=settings.APP_MODE.upper(),
        database_type=settings.DATABASE_TYPE,
        database_status=db_status["status"],
        cache_type=settings.CACHE_TYPE,
        environment=settings.ENVIRONMENT,
        total_requests=total_requests,
        execution_mode=global_pipeline.get_execution_mode()
    )

# ============================================================================
# Model Registry & Provider Execution APIs
# ============================================================================
class GenerateRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = None
    tier: Optional[ModelTier] = None
    simulate_failure: bool = False

class AnalyzeRequest(BaseModel):
    prompt: str

class PromptAnalysisRequest(BaseModel):
    prompt: str
    context: Optional[str] = None

@app.post(
    "/api/v1/analyze",
    response_model=AnalysisResult,
    summary="Semantic Request Analysis & Telemetry Profiling",
    tags=["Analysis"]
)
def analyze_request(req: PromptAnalysisRequest) -> AnalysisResult:
    """
    Evaluates incoming request across intent, task_type, complexity, sensitivity,
    criticality, priority, token estimation, and SLA requirements.
    """
    return RequestAnalyzer.analyze(req.prompt, req.context)

# ============================================================================
# Phase 1: Intelligent Routing Engine API
# ============================================================================
router_engine = IntelligentRouter()

class RoutePreviewRequest(BaseModel):
    prompt: str
    department: Optional[str] = "general"
    priority: Optional[str] = None
    sensitivity: Optional[str] = None
    required_quality: Optional[float] = None
    latency_requirement: Optional[str] = None
    custom_budget: Optional[Dict[str, float]] = None
    custom_policy: Optional[Dict[str, Any]] = None
    context: Optional[str] = None

@app.post(
    "/api/v1/route/preview",
    response_model=RoutingDecisionResult,
    summary="Intelligent LLM Model Route Preview & Cost Analysis",
    tags=["Routing"]
)
def preview_route(req: RoutePreviewRequest) -> RoutingDecisionResult:
    """
    Evaluates incoming request through the 8-step intelligent routing engine,
    applying quality constraints, SLA latency boundaries, policy allowlists,
    and budget availability to pick the lowest cost optimal model.
    """
    return router_engine.route(
        prompt=req.prompt,
        department=req.department or "general",
        priority=req.priority,
        sensitivity=req.sensitivity,
        required_quality=req.required_quality,
        latency_requirement=req.latency_requirement,
        custom_budget=req.custom_budget,
        custom_policy=req.custom_policy,
        context=req.context
    )

# ============================================================================
# Phase 2: Complete LLM Execution, Quality Guardrail, Cost & Cache APIs
# ============================================================================
@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    summary="End-to-End LLM Execution, Quality Guardrails & FinOps Cost Pipeline",
    tags=["Execution"]
)
def execute_chat(
    req: ChatRequest,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Executes an incoming request through the complete NEXUS pipeline:
    Request -> Analyzer -> Policy/Budget -> Router -> Cache -> Model Execution
    -> Quality Evaluation -> Fallback (if needed) -> Token & Cost Accounting -> DB.
    """
    return global_pipeline.execute(req, db_session=db)

@app.get(
    "/api/v1/cache/stats",
    response_model=CacheStats,
    summary="Get Semantic Cache Metrics and Savings",
    tags=["Cache"]
)
def get_cache_stats() -> CacheStats:
    """Returns total entries, hits, misses, hit rate, and total cost saved."""
    return global_cache.get_stats()

@app.post(
    "/api/v1/cache/clear",
    summary="Clear Semantic Cache",
    tags=["Cache"]
)
def clear_cache():
    """Flushes all entries from semantic cache and resets metrics."""
    global_cache.clear()
    return {"status": "success", "message": "Cache successfully cleared"}

# ============================================================================
# Phase 3: Autonomous FinOps Advisor, What-If Simulator & Analytics APIs
# ============================================================================
@app.get(
    "/api/v1/analytics/summary",
    response_model=AnalyticsSummary,
    summary="Executive FinOps KPI Summary & Baseline vs Optimized Comparison",
    tags=["Analytics"]
)
def get_analytics_summary(db: Session = Depends(get_db)) -> AnalyticsSummary:
    return AnalyticsEngine.get_summary(db)

@app.get(
    "/api/v1/analytics/cost",
    response_model=List[CostOverTimePoint],
    summary="Chronological AI Spend Over Time vs Baseline",
    tags=["Analytics"]
)
def get_analytics_cost(db: Session = Depends(get_db)) -> List[CostOverTimePoint]:
    return AnalyticsEngine.get_cost_analytics(db)

@app.get(
    "/api/v1/analytics/quality",
    response_model=List[QualityVsCostPoint],
    summary="Model Tier Quality vs Cost Trade-offs",
    tags=["Analytics"]
)
def get_analytics_quality(db: Session = Depends(get_db)) -> List[QualityVsCostPoint]:
    return AnalyticsEngine.get_quality_analytics(db)

@app.get(
    "/api/v1/analytics/routing",
    summary="Model Usage & Departmental Routing Distribution",
    tags=["Analytics"]
)
def get_analytics_routing(db: Session = Depends(get_db)):
    return AnalyticsEngine.get_routing_analytics(db)

@app.get(
    "/api/v1/finops/recommendations",
    response_model=List[FinOpsRecommendation],
    summary="Autonomous FinOps Optimization Recommendations",
    tags=["FinOps Advisor"]
)
def list_finops_recommendations(db: Session = Depends(get_db)) -> List[FinOpsRecommendation]:
    return FinOpsAdvisor.get_recommendations(db)

@app.post(
    "/api/v1/finops/recommendations/{rec_id}/apply",
    response_model=FinOpsRecommendation,
    summary="Apply FinOps Recommendation to Dynamic Policy Engine",
    tags=["FinOps Advisor"]
)
def apply_finops_recommendation(rec_id: str) -> FinOpsRecommendation:
    rec = FinOpsAdvisor.apply_recommendation(rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found")
    return rec

@app.post(
    "/api/v1/simulate",
    response_model=SimulateResponse,
    summary="What-If Model Simulator: Compare Small, Medium, and Advanced",
    tags=["What-If Simulator"]
)
def simulate_model_tradeoffs(req: SimulateRequest) -> SimulateResponse:
    return ModelSimulator.simulate(req.prompt, req.required_quality)



@app.get(
    "/api/v1/models",
    response_model=List[ModelMetadata],
    summary="List All Registered Models & Tiers",
    tags=["Models"]
)
def list_models(
    tier: Optional[ModelTier] = Query(None, description="Filter by model tier (SMALL, MEDIUM, ADVANCED)")
) -> List[ModelMetadata]:
    """
    Returns all registered models with specification real values:
    - Small: cost=0.01, latency=0.5s, quality=82
    - Medium: cost=0.05, latency=1.2s, quality=91
    - Advanced: cost=0.20, latency=2.8s, quality=97
    """
    models = get_registered_models()
    if tier:
        models = [m for m in models if m.tier == tier]
    return models

@app.get(
    "/api/v1/models/{model_id}",
    response_model=ModelMetadata,
    summary="Get Specific Model Metadata",
    tags=["Models"]
)
def get_model(model_id: str) -> ModelMetadata:
    model = get_model_metadata(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry")
    return model

@app.post(
    "/api/v1/models/generate",
    response_model=GenerationResponse,
    summary="Generate Completion via Active Provider",
    tags=["Models"]
)
def generate_completion(req: GenerateRequest) -> GenerationResponse:
    provider = get_provider()
    return provider.generate(
        prompt=req.prompt,
        model_id=req.model_id,
        tier=req.tier,
        simulate_failure=req.simulate_failure
    )

@app.post(
    "/api/v1/models/analyze",
    response_model=AnalysisResponse,
    summary="Analyze Prompt and Recommend Optimal Tier",
    tags=["Models"]
)
def analyze_prompt(req: AnalyzeRequest) -> AnalysisResponse:
    provider = get_provider()
    return provider.analyze(prompt=req.prompt)

# ============================================================================
# Request Records API
# ============================================================================
@app.post(
    "/api/v1/requests",
    response_model=RequestResponse,
    status_code=201,
    summary="Log or Ingest Request Record",
    tags=["Requests"]
)
def create_request(
    request_in: RequestCreate,
    db: Session = Depends(get_db)
):
    return DatabaseRepository.create_request(db, request_in)

@app.get(
    "/api/v1/requests/{request_id}",
    response_model=RequestResponse,
    summary="Get Request Record by ID",
    tags=["Requests"]
)
def get_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    record = DatabaseRepository.get_request(db, request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Request record not found")
    return record

@app.patch(
    "/api/v1/requests/{request_id}",
    response_model=RequestResponse,
    summary="Update Request Record",
    tags=["Requests"]
)
def update_request(
    request_id: str,
    update_in: RequestUpdate,
    db: Session = Depends(get_db)
):
    record = DatabaseRepository.update_request(db, request_id, update_in)
    if not record:
        raise HTTPException(status_code=404, detail="Request record not found")
    return record

@app.get(
    "/api/v1/requests",
    response_model=List[RequestResponse],
    summary="List Request Records",
    tags=["Requests"]
)
def list_requests(
    department: Optional[str] = Query(None, description="Filter by department"),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return DatabaseRepository.list_requests(
        db, limit=limit, offset=offset, department=department, model_id=model_id
    )

@app.get("/", tags=["System"])
def root():
    return {
        "service": "NEXUS AI FINOPS",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
        "models": "/api/v1/models"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
