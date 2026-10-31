import sys
import os
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

scripts_path = Path(__file__).resolve().parent.parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

from database.connection import init_db, SessionLocal, engine
from database.models import (
    Base,
    User,
    RequestRecord,
    ModelRegistry,
    ModelUsage,
    RoutingDecision,
    Budget,
    Policy,
    CacheEntry,
    QualityEvaluation,
    DailyMetric
)
from database.schemas import RequestCreate, RequestUpdate
from database.repository import DatabaseRepository
from seed_real_data import seed_database

@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()

def test_1_database_initialization(db_session):
    """
    1. Verify Database Initialization:
       Ensure all 10 required tables and their schemas exist.
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    required_tables = [
        "users",
        "requests",
        "model_registry",
        "model_usage",
        "routing_decisions",
        "budgets",
        "policies",
        "cache_entries",
        "quality_evaluations",
        "daily_metrics"
    ]

    for table in required_tables:
        assert table in table_names, f"Table '{table}' missing from database!"

def test_2_and_3_insert_and_read_request(db_session):
    """
    2. Insert Request & 3. Read Request:
       Create a request with all required fields and retrieve it.
    """
    test_req = RequestCreate(
        request_id="test_req_mod1_001",
        tenant_id="test-tenant",
        user_id="usr_eng_01",
        department="Engineering",
        prompt="Write a Python script for FinOps database abstraction.",
        task_type="code_generation",
        complexity="medium",
        sensitivity="internal",
        criticality="high",
        priority="high",
        selected_model="gpt-4o",
        provider="openai",
        input_tokens=1500,
        output_tokens=500,
        total_tokens=2000,
        estimated_cost=0.00875,
        actual_cost=0.00875,
        latency=480.5,
        quality_score=0.96,
        cache_hit=False,
        fallback_used=False,
        success=True,
        routing_reason="tier_matching_optimization"
    )

    created = DatabaseRepository.create_request(db_session, test_req)
    assert created is not None
    assert created.request_id == "test_req_mod1_001"

    # Read request
    retrieved = DatabaseRepository.get_request(db_session, "test_req_mod1_001")
    assert retrieved is not None
    assert retrieved.request_id == "test_req_mod1_001"
    assert retrieved.department == "Engineering"
    assert retrieved.selected_model == "gpt-4o"
    assert retrieved.total_tokens == 2000
    assert retrieved.estimated_cost == 0.00875
    assert retrieved.success is True

def test_4_update_request(db_session):
    """
    4. Update Request:
       Update actual_cost, latency, quality_score, and routing_reason.
    """
    update_data = RequestUpdate(
        actual_cost=0.00000,
        latency=18.2,
        quality_score=0.99,
        success=True,
        routing_reason="semantic_cache_hit"
    )

    updated = DatabaseRepository.update_request(db_session, "test_req_mod1_001", update_data)
    assert updated is not None
    assert updated.actual_cost == 0.00000
    assert updated.latency == 18.2
    assert updated.quality_score == 0.99
    assert updated.routing_reason == "semantic_cache_hit"

    # Read back to ensure persistence
    persisted = DatabaseRepository.get_request(db_session, "test_req_mod1_001")
    assert persisted.actual_cost == 0.00000
    assert persisted.latency == 18.2

def test_5_and_6_seed_and_verify_real_data(db_session):
    """
    5. Seed real Data & 6. Verify Seeded Records:
       Run seed script and verify at least 500 requests, all departments,
       all tiers, cache hits, fallbacks, and failures.
    """
    result = seed_database(550)
    assert result["total_seeded"] >= 500

    # Verify total requests
    total_count = DatabaseRepository.count_requests(db_session)
    assert total_count >= 500, f"Expected >= 500 requests, got {total_count}"

    # Verify all 4 departments are represented
    depts = [r[0] for r in db_session.query(RequestRecord.department).distinct().all()]
    assert set(["Engineering", "Finance", "HR", "Marketing"]).issubset(set(depts))

    # Verify all 3 tiers are in model registry and used
    tiers = [m[0] for m in db_session.query(ModelRegistry.tier).distinct().all()]
    assert set(["Small", "Medium", "Advanced"]).issubset(set(tiers))

    # Verify cache hits exist
    cache_hits_count = db_session.query(RequestRecord).filter(RequestRecord.cache_hit.is_(True)).count()
    assert cache_hits_count > 0, "No cache hits found in seeded data!"

    # Verify fallback events exist
    fallback_count = db_session.query(RequestRecord).filter(RequestRecord.fallback_used.is_(True)).count()
    assert fallback_count > 0, "No fallback events found in seeded data!"

    # Verify failures exist
    failure_count = db_session.query(RequestRecord).filter(RequestRecord.success.is_(False)).count()
    assert failure_count > 0, "No failure events found in seeded data!"

    # Verify daily metrics were populated
    metrics_count = db_session.query(DailyMetric).count()
    assert metrics_count > 0, "Daily metrics not populated!"

    # Verify budgets were updated
    budgets = db_session.query(Budget).all()
    assert len(budgets) == 4
    for b in budgets:
        assert b.spent_amount > 0, f"Budget for {b.department} has 0 spend!"

