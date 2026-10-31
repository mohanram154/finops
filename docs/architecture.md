# NEXUS AI FINOPS — Architecture & Specification

## Overview
**NEXUS AI FINOPS** is an autonomous cloud financial operations platform built for multi-cloud cost observability, anomaly detection, optimization recommendations, and automated budget guardrails.

## Technology Stack
- **Backend**:
  - Python 3.14
  - FastAPI (High performance ASGI asynchronous web framework)
  - Pydantic v2 (Strict data models and runtime validation)
  - Uvicorn (ASGI server)
- **Frontend**:
  - React 19
  - Vite 8
  - TypeScript
  - Tailwind CSS v4
  - Recharts (Cloud financial analytics & charts)
  - Lucide React (FinOps icons)
- **Persistence Strategy**:
  1. **MongoDB** (If available in environment)
  2. **PostgreSQL** (If MongoDB is absent but Postgres is detected)
  3. **SQLite** (Default fallback for self-contained, zero-dependency storage)
- **Caching Strategy**:
  1. **Redis** (If Redis server is accessible)
  2. **In-Memory Cache** (Zero-dependency fallback)

## Dual Operating Modes
NEXUS AI FINOPS supports two core execution modes toggled via `APP_MODE`:
1. **real / SIMULATION MODE** (`APP_MODE=real` or `simulation`):
   - Generates realistic synthetic multi-cloud cost streams (AWS, Azure, GCP).
   - Generates synthetic anomalies, cost spikes, and AI optimization recommendations.
   - Requires zero third-party cloud credentials or external API keys.
2. **REAL API MODE** (`APP_MODE=real`):
   - Connects to real cloud provider cost APIs (AWS Cost Explorer, Azure Cost Management, GCP Cloud Billing).
   - Uses real LLM APIs (OpenAI / Anthropic / Gemini) for root-cause cost analysis.

## Endpoints (Module 0)
- `GET /api/v1/health`
  - Specification response:
    ```json
    {
      "status": "healthy",
      "service": "nexus-ai-finops"
    }
    ```
- `GET /api/v1/system/info`
  - Returns current mode, database engine, cache type, and environment info.

