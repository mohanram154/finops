from pydantic import BaseModel
from typing import Optional

class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "nexus-ai-finops"

class AppConfigInfo(BaseModel):
    service: str = "nexus-ai-finops"
    app_mode: str
    database_type: str
    database_status: str = "connected"
    cache_type: str
    environment: str
    total_requests: int = 0
    execution_mode: str = "real / SIMULATION"
