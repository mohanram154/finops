import os
import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.analyzer import RequestAnalyzer, AnalysisResult
from app.routing.router import IntelligentRouter, RoutingDecisionResult
from app.routing.policy_engine import PolicyEngine
from app.routing.budget_engine import BudgetEngine
from .providers.base import BaseModelProvider, ModelExecutionResponse
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.real_provider import UniversalRealProvider
from .providers.simulation_provider import SimulationProvider
from .cache import global_cache, CachedResponse
from .quality_evaluator import QualityEvaluator, QualityEvaluationResult
from .cost_engine import CostEngine, CostAccountingResult, BaselineComparison
from .fallback_engine import FallbackEngine, FallbackRecord, FallbackAttempt

# ============================================================================
# Chat Request & Response Schemas
# ============================================================================
class ChatRequest(BaseModel):
    prompt: str
    department: Optional[str] = "general"
    priority: Optional[str] = None
    sensitivity: Optional[str] = None
    required_quality: Optional[float] = None
    latency_requirement: Optional[str] = None
    custom_budget: Optional[Dict[str, float]] = None
    custom_policy: Optional[Dict[str, Any]] = None
    use_cache: bool = True
    force_quality: Optional[float] = None  # Diagnostic hook to test quality guardrail (e.g. force 86)
    simulate_failure: bool = False       # Diagnostic hook to test execution failure

class ChatResponse(BaseModel):
    request_id: str
    response: str
    selected_model: str
    final_model: str
    routing_reason: List[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    quality_score: float
    latency_ms: float
    cache_hit: bool
    fallback_used: bool
    success: bool
    execution_mode: str  # "simulation" or "ollama"
    fallback_details: Optional[FallbackRecord] = None
    quality_details: Optional[QualityEvaluationResult] = None
    baseline_comparison: Optional[BaselineComparison] = None
    copilot_explanation: Optional[str] = None
    analysis: Optional[AnalysisResult] = None

# ============================================================================
# Complete Execution Pipeline Engine
# ============================================================================
class ExecutionPipeline:
    """
    Complete end-to-end LLM Execution, Quality Guardrail, Cost Engine,
    Semantic Cache & Automated Fallback Pipeline for NEXUS AI FINOPS.
    """

    def __init__(self):
        self.router = IntelligentRouter()
        self.ollama = OllamaProvider()
        self.real_provider = UniversalRealProvider()
        self.simulator = SimulationProvider()
        self.cache = global_cache

    def get_execution_mode(self) -> str:
        """Reports whether Real API (Gemini/Groq/OpenAI) or Ollama is live or running in Simulation mode."""
        app_mode = os.getenv("APP_MODE", "real").lower()
        if app_mode == "real" and self.real_provider.is_available():
            active_p = self.real_provider.get_active_provider_name()
            return f"LIVE {active_p.upper()} API"
        if self.ollama.is_available():
            return "LOCAL OLLAMA"
        return "real / SIMULATION"

    def execute(self, req: ChatRequest, db_session=None) -> ChatResponse:
        start_time = time.perf_counter()
        req_id = f"req_{uuid.uuid4().hex[:12]}"
        department = req.department or "general"

        # --------------------------------------------------------------------
        # 1. Analyze Request (Existing Module 3 Request Analyzer)
        # --------------------------------------------------------------------
        analysis: AnalysisResult = RequestAnalyzer.analyze(req.prompt)
        target_quality = req.required_quality if req.required_quality is not None else analysis.required_quality

        # --------------------------------------------------------------------
        # 2. Check Semantic Cache
        # --------------------------------------------------------------------
        if req.use_cache:
            cached_entry: Optional[CachedResponse] = self.cache.get(req.prompt)
            if cached_entry:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                baseline_comp = CostEngine.compare_with_baseline(
                    optimized_cost=0.0,
                    total_tokens=cached_entry.input_tokens + cached_entry.output_tokens
                )
                
                # Persist cache hit to database if available
                if db_session:
                    self._persist_to_database(
                        db=db_session,
                        req_id=req_id,
                        dept=department,
                        prompt=req.prompt,
                        task_type=analysis.task_type.value,
                        complexity=analysis.complexity.value,
                        sensitivity=analysis.sensitivity.value,
                        criticality=analysis.business_criticality.value,
                        priority=analysis.priority.value,
                        selected_model=cached_entry.model,
                        final_model=cached_entry.model,
                        in_tokens=cached_entry.input_tokens,
                        out_tokens=cached_entry.output_tokens,
                        cost=0.0,
                        latency_ms=elapsed_ms,
                        quality=cached_entry.quality,
                        cache_hit=True,
                        fallback_used=False,
                        success=True,
                        reason="semantic_cache_hit"
                    )

                return ChatResponse(
                    request_id=req_id,
                    response=cached_entry.response,
                    selected_model=cached_entry.model,
                    final_model=cached_entry.model,
                    routing_reason=["Semantic Cache Hit: Retrieved verified completion from cache; model invocation avoided."],
                    input_tokens=cached_entry.input_tokens,
                    output_tokens=cached_entry.output_tokens,
                    total_tokens=cached_entry.input_tokens + cached_entry.output_tokens,
                    cost=0.0,
                    quality_score=cached_entry.quality,
                    latency_ms=elapsed_ms,
                    cache_hit=True,
                    fallback_used=False,
                    success=True,
                    execution_mode="cache",
                    baseline_comparison=baseline_comp,
                    copilot_explanation=f"CACHE HIT: Served from local semantic cache. Instant sub-millisecond response with 100% token cost savings.",
                    analysis=analysis
                )

        # --------------------------------------------------------------------
        # 3. Intelligent Routing Decision (Phase 1 Router)
        # --------------------------------------------------------------------
        route_decision: RoutingDecisionResult = self.router.route(
            prompt=req.prompt,
            department=department,
            priority=req.priority,
            sensitivity=req.sensitivity,
            required_quality=target_quality,
            latency_requirement=req.latency_requirement,
            custom_policy=req.custom_policy,
            custom_budget=req.custom_budget,
            request_id=req_id
        )

        # Handle Constraint / Budget Failure (Never silently violate budget)
        if route_decision.status == "constraint_failure" or not route_decision.selected_model:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            block_msg = (
                "Request cannot be executed because available models cannot satisfy "
                "the required quality and remaining budget constraints."
            )
            return ChatResponse(
                request_id=req_id,
                response=block_msg,
                selected_model="none",
                final_model="none",
                routing_reason=route_decision.selection_reason,
                input_tokens=analysis.estimated_input_tokens,
                output_tokens=0,
                total_tokens=analysis.estimated_input_tokens,
                cost=0.0,
                quality_score=0.0,
                latency_ms=elapsed_ms,
                cache_hit=False,
                fallback_used=False,
                success=False,
                execution_mode="blocked",
                copilot_explanation=route_decision.copilot_explanation or block_msg,
                analysis=analysis
            )

        selected_model = route_decision.selected_model
        selected_tier = route_decision.tier.lower() if route_decision.tier else "small"
        alternatives = [a.model_dump() for a in route_decision.alternatives]

        # --------------------------------------------------------------------
        # 4. Model Execution (Live Cloud API: Gemini/Groq/OpenAI, Ollama Local, or Simulation)
        # --------------------------------------------------------------------
        app_mode = os.getenv("APP_MODE", "real").lower()
        if app_mode == "real":
            if not self.real_provider.is_available():
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                err_msg = "REAL mode is enabled but no valid LLM provider is configured."
                return ChatResponse(
                    request_id=req_id,
                    response=err_msg,
                    selected_model=selected_model,
                    final_model=selected_model,
                    routing_reason=route_decision.selection_reason,
                    input_tokens=analysis.estimated_input_tokens,
                    output_tokens=0,
                    total_tokens=analysis.estimated_input_tokens,
                    cost=0.0,
                    quality_score=0.0,
                    latency_ms=elapsed_ms,
                    cache_hit=False,
                    fallback_used=False,
                    success=False,
                    execution_mode="error",
                    copilot_explanation=err_msg,
                    analysis=analysis
                )
            active_provider: BaseModelProvider = self.real_provider
            execution_mode = self.real_provider.get_active_provider_name() or "real"
        elif self.ollama.is_available():
            active_provider: BaseModelProvider = self.ollama
            execution_mode = "ollama"
        else:
            active_provider: BaseModelProvider = self.simulator
            execution_mode = "simulation"

        attempts: List[FallbackAttempt] = []

        # First Execution Attempt with selected model
        exec_res: ModelExecutionResponse = active_provider.generate(
            prompt=req.prompt,
            model_id=selected_model,
            tier=selected_tier,
            required_quality=target_quality,
            force_quality=req.force_quality,
            simulate_failure=req.simulate_failure
        )

        # In simulation/demo mode: graceful fallback to simulation if needed
        # In REAL mode: DO NOT silently overwrite with fake simulated text!
        if not exec_res.success and app_mode != "real" and not req.simulate_failure:
            err_msg = exec_res.error_message or "API quota or network issue"
            exec_res = self.simulator.generate(
                prompt=req.prompt,
                model_id=selected_model,
                tier=selected_tier,
                required_quality=target_quality,
                force_quality=req.force_quality,
                simulate_failure=False
            )
            execution_mode = f"simulation ({execution_mode} fallback: {err_msg})"

        # --------------------------------------------------------------------
        # 5. Quality Evaluation & Guardrail
        # --------------------------------------------------------------------
        eval_res = QualityEvaluator.evaluate(
            prompt=req.prompt,
            response_text=exec_res.text if exec_res.success else "",
            task_type=analysis.task_type.value,
            model_quality=exec_res.quality_score,
            required_quality=target_quality
        )

        # Check if first attempt succeeded or failed guardrail
        first_attempt_passed = exec_res.success and eval_res.success

        final_model = selected_model
        final_tier = selected_tier
        fallback_used = False
        fallback_record = None

        if not first_attempt_passed:
            # ----------------------------------------------------------------
            # 6. Fallback Engine Triggered
            # ----------------------------------------------------------------
            failure_type = "quality_threshold_breach" if exec_res.success else "execution_failure"
            fail_reason = (
                f"{selected_model.capitalize()} quality {eval_res.quality_score:.1f} < required {target_quality:.1f}"
                if exec_res.success else (exec_res.error_message or "Execution failed")
            )

            attempts.append(FallbackAttempt(
                attempt_number=1,
                model_id=selected_model,
                tier=selected_tier,
                failure_type=failure_type,
                reason=fail_reason,
                quality_score=eval_res.quality_score
            ))

            # Resolve next valid fallback model (e.g., Medium -> Advanced)
            next_model = FallbackEngine.resolve_next_model(selected_model, alternatives)

            if next_model:
                fallback_used = True
                final_model = next_model
                final_tier = "advanced" if "advanced" in next_model.lower() or "o1" in next_model.lower() else "medium"

                # Strip simulated test triggers so the recovery attempt succeeds
                import re
                fallback_prompt = re.sub(r"\[(SIMULATE_FAIL|FAIL|ERROR|TIMEOUT)\]", "", req.prompt).strip()
                fallback_prompt = fallback_prompt or req.prompt

                # Execute Fallback Model using active_provider (real provider if real mode, simulation if demo)
                fallback_exec = active_provider.generate(
                    prompt=fallback_prompt,
                    model_id=final_model,
                    tier=final_tier,
                    required_quality=target_quality,
                    force_quality=None,
                    simulate_failure=False
                )

                fallback_eval = QualityEvaluator.evaluate(
                    prompt=req.prompt,
                    response_text=fallback_exec.text if fallback_exec.success else "",
                    task_type=analysis.task_type.value,
                    model_quality=fallback_exec.quality_score,
                    required_quality=target_quality
                )

                attempts.append(FallbackAttempt(
                    attempt_number=2,
                    model_id=final_model,
                    tier=final_tier,
                    failure_type="none" if fallback_eval.success else "fallback_breach",
                    reason="Fallback succeeded" if fallback_eval.success else "Fallback quality breach",
                    quality_score=fallback_eval.quality_score
                ))

                fallback_record = FallbackEngine.build_record(
                    initial_model=selected_model,
                    fallback_model=final_model,
                    reason=fail_reason,
                    success=fallback_eval.success,
                    attempts=attempts
                )

                exec_res = fallback_exec
                eval_res = fallback_eval

        # --------------------------------------------------------------------
        # 7. Token Accounting & Cost Engine
        # --------------------------------------------------------------------
        cost_res: CostAccountingResult = CostEngine.calculate(
            model=final_model,
            tier=final_tier,
            input_tokens=exec_res.input_tokens,
            output_tokens=exec_res.output_tokens
        )

        # Baseline comparison (Advanced unoptimized vs NEXUS actual cost)
        baseline_comp = CostEngine.compare_with_baseline(
            optimized_cost=cost_res.total_cost,
            total_tokens=cost_res.total_tokens
        )

        # Deduct from departmental budget
        BudgetEngine.record_spend(department, cost_res.total_cost)

        # --------------------------------------------------------------------
        # 8. Save to Semantic Cache if successful
        # --------------------------------------------------------------------
        if exec_res.success and eval_res.success and req.use_cache:
            self.cache.set(
                prompt=req.prompt,
                response=exec_res.text,
                model=final_model,
                tier=final_tier,
                quality=eval_res.quality_score,
                cost=cost_res.total_cost,
                input_tokens=exec_res.input_tokens,
                output_tokens=exec_res.output_tokens
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # --------------------------------------------------------------------
        # 9. Persist Outcome to Database (Module 1 Schema)
        # --------------------------------------------------------------------
        if db_session:
            self._persist_to_database(
                db=db_session,
                req_id=req_id,
                dept=department,
                prompt=req.prompt,
                task_type=analysis.task_type.value,
                complexity=analysis.complexity.value,
                sensitivity=analysis.sensitivity.value,
                criticality=analysis.business_criticality.value,
                priority=analysis.priority.value,
                selected_model=selected_model,
                final_model=final_model,
                in_tokens=cost_res.input_tokens,
                out_tokens=cost_res.output_tokens,
                cost=cost_res.total_cost,
                latency_ms=elapsed_ms,
                quality=eval_res.quality_score,
                cache_hit=False,
                fallback_used=fallback_used,
                success=eval_res.success,
                reason="; ".join(route_decision.selection_reason[:2])
            )

        return ChatResponse(
            request_id=req_id,
            response=exec_res.text if exec_res.success else (exec_res.error_message or "Execution failed"),
            selected_model=selected_model,
            final_model=final_model,
            routing_reason=route_decision.selection_reason,
            input_tokens=cost_res.input_tokens,
            output_tokens=cost_res.output_tokens,
            total_tokens=cost_res.total_tokens,
            cost=cost_res.total_cost,
            quality_score=eval_res.quality_score,
            latency_ms=elapsed_ms,
            cache_hit=False,
            fallback_used=fallback_used,
            success=exec_res.success and eval_res.success,
            execution_mode=execution_mode,
            fallback_details=fallback_record,
            quality_details=eval_res,
            baseline_comparison=baseline_comp,
            copilot_explanation=route_decision.copilot_explanation,
            analysis=analysis
        )

    def _persist_to_database(
        self, db, req_id: str, dept: str, prompt: str, task_type: str,
        complexity: str, sensitivity: str, criticality: str, priority: str,
        selected_model: str, final_model: str, in_tokens: int, out_tokens: int,
        cost: float, latency_ms: float, quality: float, cache_hit: bool,
        fallback_used: bool, success: bool, reason: str
    ):
        try:
            from database.models import RequestRecord
            record = RequestRecord(
                request_id=req_id,
                tenant_id="default-tenant",
                timestamp=datetime.now(timezone.utc),
                user_id="user_chat",
                department=dept,
                prompt=prompt,
                task_type=task_type,
                complexity=complexity,
                sensitivity=sensitivity,
                criticality=criticality,
                priority=priority,
                selected_model=final_model,
                provider="simulation",
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                total_tokens=in_tokens + out_tokens,
                estimated_cost=cost,
                actual_cost=cost,
                latency=latency_ms,
                quality_score=quality / 100.0 if quality > 1.0 else quality,
                cache_hit=cache_hit,
                fallback_used=fallback_used,
                success=success,
                routing_reason=reason
            )
            db.add(record)
            db.commit()
        except Exception:
            pass  # Fail-safe database commit for hackathon speed

