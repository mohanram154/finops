import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import app, get_health, get_system_info
from models import HealthResponse, AppConfigInfo

def test_health_endpoint_response():
    """
    Test MODULE 0 Specification:
    GET /api/v1/health -> { "status": "healthy", "service": "nexus-ai-finops" }
    """
    response: HealthResponse = get_health()
    assert response.status == "healthy"
    assert response.service == "nexus-ai-finops"
    assert response.model_dump() == {
        "status": "healthy",
        "service": "nexus-ai-finops"
    }

def test_health_route_registration():
    """
    Ensure /api/v1/health route is registered on FastAPI app with GET method.
    """
    health_routes = [
        route for route in app.routes
        if getattr(route, "path", None) == "/api/v1/health"
    ]
    assert len(health_routes) == 1
    route = health_routes[0]
    assert "GET" in route.methods
    assert route.response_model == HealthResponse

def test_system_info_modes():
    """
    Test real/SIMULATION and REAL API mode configuration support.
    """
    info: AppConfigInfo = get_system_info()
    assert info.service == "nexus-ai-finops"
    assert info.app_mode in ["real", "SIMULATION", "REAL"]
    assert info.database_type in ["sqlite", "mongodb", "postgresql"]
    assert info.cache_type in ["inmemory", "redis"]
