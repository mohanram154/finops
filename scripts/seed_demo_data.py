"""
NEXUS AI FINOPS — Historical real Data Seeder
Seeds at least 500+ realistic multi-cloud LLM requests across Engineering, Finance, HR, and Marketing.
Computes realistic costs, latencies, cache hits, fallbacks, failures, and aggregations.
"""

import os
import sys
import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from database.connection import init_db, SessionLocal
from database.models import (
    User,
    ModelRegistry,
    Budget,
    Policy,
    RequestRecord,
    CacheEntry,
    QualityEvaluation,
    DailyMetric,
    ModelUsage
)

# Deterministic random seed for reproducible real data
random.seed(42)

# ============================================================================
# 1. Models & Pricing Matrix
# ============================================================================
MODELS = [
    # Small Tier
    {
        "model_id": "gpt-4o-mini",
        "model_name": "GPT-4o Mini",
        "provider": "openai",
        "tier": "Small",
        "context_window": 128000,
        "cost_per_1k_input": 0.00015,
        "cost_per_1k_output": 0.00060,
        "avg_latency_ms": 220.0,
        "quality_rating": 0.88,
        "is_active": True
    },
    {
        "model_id": "claude-3-haiku",
        "model_name": "Claude 3 Haiku",
        "provider": "anthropic",
        "tier": "Small",
        "context_window": 200000,
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125,
        "avg_latency_ms": 260.0,
        "quality_rating": 0.86,
        "is_active": True
    },
    {
        "model_id": "gemini-1.5-flash",
        "model_name": "Gemini 1.5 Flash",
        "provider": "google",
        "tier": "Small",
        "context_window": 1000000,
        "cost_per_1k_input": 0.000075,
        "cost_per_1k_output": 0.00030,
        "avg_latency_ms": 180.0,
        "quality_rating": 0.87,
        "is_active": True
    },
    # Medium Tier
    {
        "model_id": "gpt-4o",
        "model_name": "GPT-4o",
        "provider": "openai",
        "tier": "Medium",
        "context_window": 128000,
        "cost_per_1k_input": 0.00250,
        "cost_per_1k_output": 0.01000,
        "avg_latency_ms": 650.0,
        "quality_rating": 0.95,
        "is_active": True
    },
    {
        "model_id": "claude-3-5-sonnet",
        "model_name": "Claude 3.5 Sonnet",
        "provider": "anthropic",
        "tier": "Medium",
        "context_window": 200000,
        "cost_per_1k_input": 0.00300,
        "cost_per_1k_output": 0.01500,
        "avg_latency_ms": 720.0,
        "quality_rating": 0.97,
        "is_active": True
    },
    {
        "model_id": "gemini-1.5-pro",
        "model_name": "Gemini 1.5 Pro",
        "provider": "google",
        "tier": "Medium",
        "context_window": 2000000,
        "cost_per_1k_input": 0.00125,
        "cost_per_1k_output": 0.00500,
        "avg_latency_ms": 580.0,
        "quality_rating": 0.94,
        "is_active": True
    },
    # Advanced Tier
    {
        "model_id": "o1-preview",
        "model_name": "OpenAI o1 Reasoning",
        "provider": "openai",
        "tier": "Advanced",
        "context_window": 128000,
        "cost_per_1k_input": 0.01500,
        "cost_per_1k_output": 0.06000,
        "avg_latency_ms": 2800.0,
        "quality_rating": 0.99,
        "is_active": True
    },
    {
        "model_id": "claude-3-opus",
        "model_name": "Claude 3 Opus",
        "provider": "anthropic",
        "tier": "Advanced",
        "context_window": 200000,
        "cost_per_1k_input": 0.01500,
        "cost_per_1k_output": 0.07500,
        "avg_latency_ms": 2100.0,
        "quality_rating": 0.96,
        "is_active": True
    }
]

# ============================================================================
# 2. Departments & Domain Task Prompts
# ============================================================================
DEPARTMENT_TASKS = {
    "Engineering": [
        ("code_generation", "Generate a resilient FastAPI Redis connection pool with retry backoff and circuit breaker logic.", "high", "internal", "high"),
        ("code_review", "Review this React TypeScript hook for stale closure issues and unnecessary re-render triggers.", "medium", "internal", "medium"),
        ("bug_triage", "Analyze Kubernetes crash loop backoff logs from the billing service pod and identify the root cause.", "high", "confidential", "critical"),
        ("sql_optimization", "Optimize this PostgreSQL CTE query joining 4.2 million billing ledger rows with explain analyze.", "medium", "confidential", "medium"),
        ("unit_test_creation", "Write parameterized pytest unit tests covering edge cases for JWT token expiration and revoking.", "low", "internal", "low"),
        ("api_design", "Generate an OpenAPI 3.1 specification for a multi-tenant cloud cost anomaly alerting endpoint.", "medium", "internal", "medium"),
    ],
    "Finance": [
        ("financial_statement_audit", "Reconcile multi-cloud AWS and Azure monthly invoices against Stripe merchant payment charges.", "high", "restricted", "critical"),
        ("expense_anomaly_detection", "Analyze unexpected 34% spike in GCP BigQuery on-demand analysis slots during off-peak weekend hours.", "high", "confidential", "high"),
        ("q3_revenue_forecast", "Build a Monte Carlo simulation forecast for ARR growth based on current net retention and churn rates.", "high", "restricted", "critical"),
        ("vendor_contract_analysis", "Extract early termination penalties and SLA uptime credit formulas from Datadog enterprise renewal agreement.", "medium", "confidential", "medium"),
        ("tax_deduction_check", "Review software R&D capitalization expenses for Section 174 compliance across cross-functional engineering teams.", "high", "restricted", "high"),
    ],
    "HR": [
        ("resume_screening", "Evaluate this Senior Distributed Systems Engineer resume against required Go, Rust, and Kafka proficiencies.", "low", "confidential", "low"),
        ("job_description_drafting", "Draft an inclusive job description for a Lead FinOps Architect with cloud optimization background.", "low", "public", "low"),
        ("benefits_policy_qa", "Synthesize global parental leave and remote work travel reimbursement guidelines for employee handbook.", "low", "internal", "low"),
        ("interview_question_generator", "Generate behavioral situational interview questions assessing conflict resolution in remote engineering teams.", "low", "internal", "normal"),
        ("performance_review_summary", "Summarize peer feedback themes into actionable strengths and development opportunities for semi-annual review.", "medium", "confidential", "medium"),
    ],
    "Marketing": [
        ("seo_blog_post", "Write a 1200-word SEO-optimized technical article explaining automated FinOps Kubernetes rightsizing.", "medium", "public", "low"),
        ("ad_campaign_copy", "Generate high-converting LinkedIn and Google Search ad copy variants highlighting 40% cloud cost reduction.", "low", "public", "low"),
        ("email_newsletter", "Compose the monthly Nexus Cloud Intelligence newsletter featuring customer case study and cost benchmarking.", "medium", "public", "low"),
        ("customer_sentiment_analysis", "Categorize and score sentiment across 450 G2 user reviews regarding our automated billing dashboard.", "medium", "public", "medium"),
        ("product_launch_pitch", "Refine key value propositions and competitor comparison matrix for the upcoming AI Smart Router launch.", "high", "confidential", "high"),
    ]
}

USERS_SEED = [
    # Engineering
    {"user_id": "usr_eng_01", "name": "Elena Rostova", "email": "elena.rostova@nexus.ai", "department": "Engineering", "role": "admin"},
    {"user_id": "usr_eng_02", "name": "Marcus Vance", "email": "marcus.vance@nexus.ai", "department": "Engineering", "role": "developer"},
    {"user_id": "usr_eng_03", "name": "Priya Sharma", "email": "priya.sharma@nexus.ai", "department": "Engineering", "role": "developer"},
    # Finance
    {"user_id": "usr_fin_01", "name": "David Sterling", "email": "david.sterling@nexus.ai", "department": "Finance", "role": "manager"},
    {"user_id": "usr_fin_02", "name": "Chloe Dupont", "email": "chloe.dupont@nexus.ai", "department": "Finance", "role": "analyst"},
    # HR
    {"user_id": "usr_hr_01", "name": "Sarah Jenkins", "email": "sarah.jenkins@nexus.ai", "department": "HR", "role": "manager"},
    {"user_id": "usr_hr_02", "name": "Amir Hassan", "email": "amir.hassan@nexus.ai", "department": "HR", "role": "analyst"},
    # Marketing
    {"user_id": "usr_mkt_01", "name": "Lucas Bianchi", "email": "lucas.bianchi@nexus.ai", "department": "Marketing", "role": "manager"},
    {"user_id": "usr_mkt_02", "name": "Jessica Taylor", "email": "jessica.taylor@nexus.ai", "department": "Marketing", "role": "analyst"},
]

BUDGETS_SEED = [
    {"budget_id": "bg_eng_monthly", "department": "Engineering", "period": "monthly", "allocated_amount": 4500.0, "warning_threshold": 0.80, "hard_limit": 1.00},
    {"budget_id": "bg_fin_monthly", "department": "Finance", "period": "monthly", "allocated_amount": 1800.0, "warning_threshold": 0.85, "hard_limit": 1.00},
    {"budget_id": "bg_hr_monthly", "department": "HR", "period": "monthly", "allocated_amount": 800.0, "warning_threshold": 0.75, "hard_limit": 1.00},
    {"budget_id": "bg_mkt_monthly", "department": "Marketing", "period": "monthly", "allocated_amount": 2200.0, "warning_threshold": 0.80, "hard_limit": 1.00},
]

POLICIES_SEED = [
    {
        "policy_id": "pol_eng_default",
        "name": "Engineering SLA Guaranteed Routing",
        "description": "Permits Medium and Advanced tiers for code generation and architectural tasks.",
        "department": "Engineering",
        "max_cost_per_request": 3.50,
        "allowed_tiers": "Small,Medium,Advanced",
        "enforce_cache": True
    },
    {
        "policy_id": "pol_fin_strict",
        "name": "Finance Audit Precision & Confidentiality",
        "description": "Ensures high accuracy models for revenue and audit reconciliations.",
        "department": "Finance",
        "max_cost_per_request": 2.50,
        "allowed_tiers": "Medium,Advanced",
        "enforce_cache": False
    },
    {
        "policy_id": "pol_hr_frugal",
        "name": "HR Cost Minimization Policy",
        "description": "Restricts routine screening and policy Q&A to Small tier models.",
        "department": "HR",
        "max_cost_per_request": 0.25,
        "allowed_tiers": "Small",
        "enforce_cache": True
    },
    {
        "policy_id": "pol_mkt_cache_first",
        "name": "Marketing High Cache Utilization",
        "description": "Aggressively serves customer persona and repeated copywriting queries from cache.",
        "department": "Marketing",
        "max_cost_per_request": 1.00,
        "allowed_tiers": "Small,Medium",
        "enforce_cache": True
    }
]

def seed_database(total_requests_to_generate: int = 550) -> Dict[str, Any]:
    print("==================================================================")
    print("  NEXUS AI FINOPS — Database Seeder")
    print("==================================================================")

    init_db()
    db = SessionLocal()

    try:
        # 1. Clean existing records for a fresh seed
        print("\n[1/6] Resetting existing database records...")
        db.query(RequestRecord).delete()
        db.query(DailyMetric).delete()
        db.query(ModelUsage).delete()
        db.query(CacheEntry).delete()
        db.query(QualityEvaluation).delete()
        db.query(Budget).delete()
        db.query(Policy).delete()
        db.query(User).delete()
        db.query(ModelRegistry).delete()
        db.commit()

        # 2. Seed Model Registry
        print("[2/6] Seeding Model Registry...")
        models_map = {}
        for m in MODELS:
            db_m = ModelRegistry(**m)
            db.add(db_m)
            models_map[m["model_id"]] = m
        db.commit()

        # 3. Seed Users
        print("[3/6] Seeding Users across Departments...")
        user_ids_by_dept = {}
        for u in USERS_SEED:
            db_u = User(**u)
            db.add(db_u)
            user_ids_by_dept.setdefault(u["department"], []).append(u["user_id"])
        db.commit()

        # 4. Seed Budgets and Policies
        print("[4/6] Seeding Department Budgets and Governance Policies...")
        for b in BUDGETS_SEED:
            db.add(Budget(**b))
        for p in POLICIES_SEED:
            db.add(Policy(**p))
        db.commit()

        # 5. Generate 500+ Realistic Historical Requests
        print(f"[5/6] Generating {total_requests_to_generate} realistic historical requests...")
        now = datetime.now(timezone.utc)
        departments = ["Engineering", "Finance", "HR", "Marketing"]
        
        # Dept distribution weights: Eng 40%, Mkt 25%, Fin 20%, HR 15%
        dept_weights = [0.40, 0.20, 0.15, 0.25]
        
        requests_to_insert = []
        cache_entries_created = {}
        daily_buckets = {}  # (date_str, dept) -> list of request dicts
        model_usage_buckets = {} # (date_str, model_id) -> list of request dicts

        for i in range(total_requests_to_generate):
            # Spread over last 30 days
            days_ago = random.triangular(0, 30, 7)  # skewed slightly towards recent days
            seconds_offset = random.randint(0, 86400)
            req_time = now - timedelta(days=days_ago, seconds=seconds_offset)
            date_str = req_time.strftime("%Y-%m-%d")

            # Pick department
            dept = random.choices(departments, weights=dept_weights)[0]
            user_id = random.choice(user_ids_by_dept[dept])

            # Pick task template
            task_template = random.choice(DEPARTMENT_TASKS[dept])
            task_type, prompt_base, default_complexity, sensitivity, default_criticality = task_template

            prompt = f"{prompt_base} [Sample Ref #{i+1:04d}]"
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

            # Model tier selection logic based on complexity and department
            if default_complexity == "high" or dept in ["Engineering", "Finance"] and random.random() < 0.35:
                # Advanced or Medium
                tier = random.choice(["Medium", "Advanced"] if random.random() < 0.25 else ["Medium"])
            elif default_complexity == "low" or dept == "HR":
                # Small tier
                tier = "Small"
            else:
                # Mix of Small and Medium
                tier = random.choices(["Small", "Medium"], weights=[0.45, 0.55])[0]

            candidate_models = [m for m in MODELS if m["tier"] == tier]
            model_info = random.choice(candidate_models)
            model_id = model_info["model_id"]
            provider = model_info["provider"]

            # Token calculation based on complexity
            if default_complexity == "low":
                input_tokens = random.randint(120, 600)
                output_tokens = random.randint(80, 450)
            elif default_complexity == "medium":
                input_tokens = random.randint(600, 2200)
                output_tokens = random.randint(350, 1100)
            else:
                input_tokens = random.randint(2200, 6500)
                output_tokens = random.randint(800, 2800)

            total_tokens = input_tokens + output_tokens

            # Theoretical estimated cost
            estimated_cost = (
                (input_tokens * model_info["cost_per_1k_input"]) +
                (output_tokens * model_info["cost_per_1k_output"])
            ) / 1000.0

            # Determine simulation events:
            # - Cache hit (~18%)
            # - Fallback event (~5%)
            # - Failure (~3%)
            roll = random.random()
            is_cache_hit = False
            is_fallback = False
            is_success = True
            routing_reason = "cost_minimization"

            if roll < 0.18:
                # Semantic cache hit
                is_cache_hit = True
                actual_cost = 0.00000
                latency = round(random.uniform(14.0, 42.0), 2)  # fast sub-50ms cache response
                quality_score = round(random.uniform(0.92, 0.99), 3)
                routing_reason = "semantic_cache_hit"

                if prompt_hash not in cache_entries_created:
                    cache_entries_created[prompt_hash] = {
                        "cache_key": f"cache:{dept.lower()}:{prompt_hash}",
                        "tenant_id": "default-tenant",
                        "prompt_hash": prompt_hash,
                        "task_type": task_type,
                        "model_id": model_id,
                        "response_text": f"Cached verified output for {task_type}.",
                        "tokens_saved": total_tokens,
                        "cost_saved": estimated_cost,
                        "hit_count": 1,
                        "created_at": req_time,
                        "last_accessed": req_time
                    }
                else:
                    cache_entries_created[prompt_hash]["hit_count"] += 1
                    cache_entries_created[prompt_hash]["tokens_saved"] += total_tokens
                    cache_entries_created[prompt_hash]["cost_saved"] += estimated_cost
                    cache_entries_created[prompt_hash]["last_accessed"] = req_time

            elif roll < 0.23:
                # Fallback event (~5%)
                is_fallback = True
                # e.g., Medium failed or hit rate limit, fell back to backup provider or Small/Medium
                actual_cost = round(estimated_cost * 1.05, 6)
                latency = round(model_info["avg_latency_ms"] * random.uniform(1.3, 1.9), 2)
                quality_score = round(random.uniform(0.85, 0.93), 3)
                routing_reason = random.choice([
                    "provider_rate_limit_fallback",
                    "latency_sla_breach_fallback",
                    "concurrency_saturation_fallback"
                ])

            elif roll < 0.26:
                # Failure event (~3%)
                is_success = False
                actual_cost = 0.00000
                latency = round(random.uniform(2500.0, 5000.0), 2)  # timeout
                quality_score = 0.0
                routing_reason = random.choice([
                    "upstream_provider_504_timeout",
                    "token_context_window_exceeded",
                    "provider_authentication_rejection"
                ])

            else:
                # Normal direct execution
                actual_cost = round(estimated_cost, 6)
                latency_jitter = random.uniform(0.80, 1.25)
                latency = round(model_info["avg_latency_ms"] * latency_jitter, 2)
                quality_score = round(random.uniform(0.88, 0.98), 3)
                routing_reason = random.choice([
                    "tier_matching_optimization",
                    "cost_minimization",
                    "sla_guarantee",
                    "budget_conservation"
                ])

            req_dict = {
                "request_id": f"req_{i+1:06d}_{prompt_hash[:8]}",
                "tenant_id": "default-tenant",
                "timestamp": req_time,
                "user_id": user_id,
                "department": dept,
                "prompt": prompt,
                "task_type": task_type,
                "complexity": default_complexity,
                "sensitivity": sensitivity,
                "criticality": default_criticality,
                "priority": "high" if default_criticality in ["high", "critical"] else "normal",
                "selected_model": model_id,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": round(estimated_cost, 6),
                "actual_cost": actual_cost,
                "latency": latency,
                "quality_score": quality_score,
                "cache_hit": is_cache_hit,
                "fallback_used": is_fallback,
                "success": is_success,
                "routing_reason": routing_reason
            }
            requests_to_insert.append(req_dict)

            # Bucket for daily metrics
            daily_key = (date_str, dept)
            daily_buckets.setdefault(daily_key, []).append(req_dict)

            # Bucket for model usage
            model_key = (date_str, model_id)
            model_usage_buckets.setdefault(model_key, []).append(req_dict)

        # Bulk save requests
        req_objects = [RequestRecord(**r) for r in requests_to_insert]
        db.bulk_save_objects(req_objects)
        db.commit()

        # Seed Cache Entries
        for c in cache_entries_created.values():
            db.add(CacheEntry(**c))
        db.commit()

        # Seed Quality Evaluations (for high criticality requests)
        high_crit_reqs = [r for r in requests_to_insert if r["criticality"] in ["high", "critical"] and r["success"]][:60]
        for h in high_crit_reqs:
            eval_record = QualityEvaluation(
                eval_id=f"eval_{h['request_id']}",
                request_id=h["request_id"],
                model_id=h["selected_model"],
                evaluation_type="automated",
                accuracy_score=round(random.uniform(0.92, 0.99), 3),
                hallucination_detected=False,
                latency_satisfaction=0.95 if h["latency"] < 1000 else 0.88,
                cost_efficiency_score=0.92,
                overall_score=h["quality_score"],
                feedback="High financial relevance with accurate parameter estimation."
            )
            db.add(eval_record)
        db.commit()

        # 6. Aggregate and Store Daily Metrics & Model Usage
        print("[6/6] Aggregating historical daily metrics and model usage...")
        for (date_str, dept), reqs in daily_buckets.items():
            tot_reqs = len(reqs)
            tot_cost = sum(r["actual_cost"] for r in reqs)
            tot_latency = sum(r["latency"] for r in reqs)
            cache_hits = sum(1 for r in reqs if r["cache_hit"])
            fallbacks = sum(1 for r in reqs if r["fallback_used"])
            errors = sum(1 for r in reqs if not r["success"])
            tot_tokens = sum(r["total_tokens"] for r in reqs)
            avg_qual = sum(r["quality_score"] for r in reqs) / tot_reqs if tot_reqs > 0 else 0.0

            dm = DailyMetric(
                date=date_str,
                tenant_id="default-tenant",
                department=dept,
                total_requests=tot_reqs,
                total_cost=round(tot_cost, 4),
                avg_latency_ms=round(tot_latency / tot_reqs, 2),
                cache_hits=cache_hits,
                cache_hit_rate=round(cache_hits / tot_reqs, 4),
                fallback_count=fallbacks,
                error_count=errors,
                avg_quality_score=round(avg_qual, 3),
                tokens_total=tot_tokens
            )
            db.add(dm)

        # Model usage aggregation
        for (date_str, model_id), reqs in model_usage_buckets.items():
            tot_reqs = len(reqs)
            succ_reqs = sum(1 for r in reqs if r["success"])
            failed_reqs = tot_reqs - succ_reqs
            tot_cost = sum(r["actual_cost"] for r in reqs)
            tot_in = sum(r["input_tokens"] for r in reqs)
            tot_out = sum(r["output_tokens"] for r in reqs)
            avg_lat = sum(r["latency"] for r in reqs) / tot_reqs if tot_reqs > 0 else 0.0

            mu = ModelUsage(
                tenant_id="default-tenant",
                model_id=model_id,
                date=date_str,
                total_requests=tot_reqs,
                successful_requests=succ_reqs,
                failed_requests=failed_reqs,
                total_input_tokens=tot_in,
                total_output_tokens=tot_out,
                total_cost=round(tot_cost, 4),
                avg_latency_ms=round(avg_lat, 2)
            )
            db.add(mu)

        # Update spent_amount in Budgets based on seeded data
        dept_costs = {}
        for r in requests_to_insert:
            dept_costs[r["department"]] = dept_costs.get(r["department"], 0.0) + r["actual_cost"]

        for b in db.query(Budget).all():
            spent = round(dept_costs.get(b.department, 0.0), 2)
            b.spent_amount = spent
            if spent >= b.allocated_amount * b.hard_limit:
                b.status = "exceeded"
            elif spent >= b.allocated_amount * b.warning_threshold:
                b.status = "warning"
            else:
                b.status = "active"

        db.commit()

        # Summary statistics
        total_seeded = len(requests_to_insert)
        total_spend = sum(r["actual_cost"] for r in requests_to_insert)
        cache_hits = sum(1 for r in requests_to_insert if r["cache_hit"])
        fallbacks = sum(1 for r in requests_to_insert if r["fallback_used"])
        failures = sum(1 for r in requests_to_insert if not r["success"])

        print("\n==================================================================")
        print("  SEEDING COMPLETE — SUMMARY")
        print("==================================================================")
        print(f"Total Requests Seeded: {total_seeded}")
        print(f"Total Cloud LLM Spend: ${total_spend:.4f}")
        print(f"Cache Hits:            {cache_hits} ({cache_hits/total_seeded*100:.1f}%)")
        print(f"Fallback Events:       {fallbacks} ({fallbacks/total_seeded*100:.1f}%)")
        print(f"Failure Events:        {failures} ({failures/total_seeded*100:.1f}%)")
        print(f"Departments Covered:   {', '.join(departments)}")
        print(f"Model Registry Count:  {len(MODELS)}")
        print(f"Daily Metric Entries:  {len(daily_buckets)}")
        print("==================================================================")

        return {
            "total_seeded": total_seeded,
            "total_spend": total_spend,
            "cache_hits": cache_hits,
            "fallbacks": fallbacks,
            "failures": failures
        }

    finally:
        db.close()

if __name__ == "__main__":
    count = 550
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            pass
    seed_database(count)
