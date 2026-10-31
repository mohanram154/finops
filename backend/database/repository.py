import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import (
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
from .schemas import RequestCreate, RequestUpdate

class DatabaseRepository:
    """
    Modular repository abstraction layer for NEXUS AI FINOPS.
    Supports SQLite and PostgreSQL natively via SQLAlchemy, and preserves
    a clean interface for future MongoDB adapter integration.
    """

    # ------------------------------------------------------------------------
    # Requests CRUD
    # ------------------------------------------------------------------------
    @staticmethod
    def create_request(db: Session, request_in: RequestCreate) -> RequestRecord:
        data = request_in.model_dump()
        if not data.get("request_id"):
            data["request_id"] = str(uuid.uuid4())
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now(timezone.utc)

        db_item = RequestRecord(**data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def get_request(db: Session, request_id: str) -> Optional[RequestRecord]:
        return db.query(RequestRecord).filter(RequestRecord.request_id == request_id).first()

    @staticmethod
    def update_request(db: Session, request_id: str, update_in: RequestUpdate) -> Optional[RequestRecord]:
        db_item = db.query(RequestRecord).filter(RequestRecord.request_id == request_id).first()
        if not db_item:
            return None

        update_data = update_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)

        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def delete_request(db: Session, request_id: str) -> bool:
        db_item = db.query(RequestRecord).filter(RequestRecord.request_id == request_id).first()
        if not db_item:
            return False
        db.delete(db_item)
        db.commit()
        return True

    @staticmethod
    def list_requests(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        department: Optional[str] = None,
        model_id: Optional[str] = None,
        tenant_id: str = "default-tenant"
    ) -> List[RequestRecord]:
        query = db.query(RequestRecord).filter(RequestRecord.tenant_id == tenant_id)
        if department:
            query = query.filter(RequestRecord.department == department)
        if model_id:
            query = query.filter(RequestRecord.selected_model == model_id)
        return query.order_by(desc(RequestRecord.timestamp)).offset(offset).limit(limit).all()

    @staticmethod
    def count_requests(db: Session, tenant_id: str = "default-tenant") -> int:
        return db.query(func.count(RequestRecord.id)).filter(RequestRecord.tenant_id == tenant_id).scalar() or 0

    @staticmethod
    def bulk_create_requests(db: Session, records: List[Dict[str, Any]]) -> int:
        objects = [RequestRecord(**r) for r in records]
        db.bulk_save_objects(objects)
        db.commit()
        return len(objects)

    # ------------------------------------------------------------------------
    # Users CRUD
    # ------------------------------------------------------------------------
    @staticmethod
    def create_user(db: Session, user_data: Dict[str, Any]) -> User:
        if not user_data.get("user_id"):
            user_data["user_id"] = str(uuid.uuid4())
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def list_users(db: Session, tenant_id: str = "default-tenant") -> List[User]:
        return db.query(User).filter(User.tenant_id == tenant_id).all()

    # ------------------------------------------------------------------------
    # Models CRUD
    # ------------------------------------------------------------------------
    @staticmethod
    def create_model(db: Session, model_data: Dict[str, Any]) -> ModelRegistry:
        model = ModelRegistry(**model_data)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def get_models(db: Session, active_only: bool = True) -> List[ModelRegistry]:
        query = db.query(ModelRegistry)
        if active_only:
            query = query.filter(ModelRegistry.is_active.is_(True))
        return query.all()

    @staticmethod
    def get_model(db: Session, model_id: str) -> Optional[ModelRegistry]:
        return db.query(ModelRegistry).filter(ModelRegistry.model_id == model_id).first()

    # ------------------------------------------------------------------------
    # Budgets & Policies CRUD
    # ------------------------------------------------------------------------
    @staticmethod
    def create_budget(db: Session, budget_data: Dict[str, Any]) -> Budget:
        if not budget_data.get("budget_id"):
            budget_data["budget_id"] = str(uuid.uuid4())
        budget = Budget(**budget_data)
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def get_budgets(db: Session, tenant_id: str = "default-tenant") -> List[Budget]:
        return db.query(Budget).filter(Budget.tenant_id == tenant_id).all()

    @staticmethod
    def create_policy(db: Session, policy_data: Dict[str, Any]) -> Policy:
        if not policy_data.get("policy_id"):
            policy_data["policy_id"] = str(uuid.uuid4())
        policy = Policy(**policy_data)
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def get_policies(db: Session, tenant_id: str = "default-tenant") -> List[Policy]:
        return db.query(Policy).filter(Policy.tenant_id == tenant_id).all()

    # ------------------------------------------------------------------------
    # Cache & Quality CRUD
    # ------------------------------------------------------------------------
    @staticmethod
    def create_cache_entry(db: Session, cache_data: Dict[str, Any]) -> CacheEntry:
        entry = CacheEntry(**cache_data)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_cache_entry(db: Session, prompt_hash: str, tenant_id: str = "default-tenant") -> Optional[CacheEntry]:
        return db.query(CacheEntry).filter(
            CacheEntry.prompt_hash == prompt_hash,
            CacheEntry.tenant_id == tenant_id
        ).first()

    @staticmethod
    def create_quality_evaluation(db: Session, eval_data: Dict[str, Any]) -> QualityEvaluation:
        if not eval_data.get("eval_id"):
            eval_data["eval_id"] = str(uuid.uuid4())
        eval_item = QualityEvaluation(**eval_data)
        db.add(eval_item)
        db.commit()
        db.refresh(eval_item)
        return eval_item

    # ------------------------------------------------------------------------
    # Daily Metrics & Analytics Aggregation
    # ------------------------------------------------------------------------
    @staticmethod
    def create_daily_metric(db: Session, metric_data: Dict[str, Any]) -> DailyMetric:
        metric = DailyMetric(**metric_data)
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def get_daily_metrics(
        db: Session,
        tenant_id: str = "default-tenant",
        department: Optional[str] = None
    ) -> List[DailyMetric]:
        query = db.query(DailyMetric).filter(DailyMetric.tenant_id == tenant_id)
        if department:
            query = query.filter(DailyMetric.department == department)
        return query.order_by(DailyMetric.date.asc()).all()
