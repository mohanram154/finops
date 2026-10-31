# NEXUS AI FINOPS

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-7+-3178C6.svg?logo=typescript)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-8+-646CFF.svg?logo=vite)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)

**NEXUS AI FINOPS** is an intelligent, autonomous LLM routing, cost governance, and financial operations engine. It eliminates enterprise AI waste by analyzing user requests in sub-milliseconds and automatically routing every query to the most cost-effective model that satisfies required quality and latency boundaries.

---

## 🚀 Key Capabilities

- **True Automatic LLM Routing**: Users never have to manually select models. NEXUS analyzes task type, complexity, and risk, automatically picking the optimal model tier (Small, Medium, or Advanced).
- **Multi-Provider LLM Integration**: Connects live with Google Gemini (`gemini-2.5-flash`), Groq Cloud (`openai/gpt-oss-20b`, `120b`), OpenAI (`gpt-4o`), and local Ollama.
- **Sub-Millisecond Semantic Cache**: Exact & normalized caching delivers instant responses in `< 0.5ms` with 100% token cost reduction.
- **Automated Quality Guardrails & Fallbacks**: Evaluates completions post-generation; if a cheaper model breaches quality constraints, NEXUS automatically escalates to a higher-tier model before returning the response.
- **Real-Time FinOps Advisor & What-If Simulator**: Continuously monitors request history, diagnoses cost anomalies, recommends rightsizing policies, and simulates hypothetical budget impacts.
- **Executive Command Center Dashboard**: Real-time KPI cards, spend over time vs. unoptimized baseline, and interactive AI Playground.

---

## 🛠️ Architecture & Tech Stack

```text
USER QUERY
    ↓
REQUEST ANALYZER (Deterministic NLP: Task, Complexity, SLA, Risk)
    ↓
SEMANTIC CACHE CHECK (0.3ms instant hit at $0 cost)
    ↓ (Cache Miss)
POLICY + BUDGET ENGINE (Allowed models, latency limits, budget caps)
    ↓
INTELLIGENT ROUTER (Lowest cost valid model candidate)
    ↓
LIVE LLM EXECUTION (Gemini 2.5 Flash / Groq / OpenAI / Ollama / Simulation)
    ↓
QUALITY GUARDRAIL (Scores response quality)
    ↓ (If breached → Automatic Fallback to higher tier)
TOKEN & COST ACCOUNTING (Unit economics vs baseline)
    ↓
PERSIST TO LEDGER & RETURN RESPONSE
```

### Full Stack Overview:
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4, Recharts, Lucide Icons.
- **Backend**: Python 3.14, FastAPI, Uvicorn, Pydantic v2, python-dotenv.
- **Database**: SQLite with Write-Ahead Logging (WAL) mode via SQLAlchemy 2.0 ORM.
- **Testing**: Pytest automated test suites covering routing, execution, analytics, and health.

---

## 📁 Repository Structure

```text
finops/
├── backend/
│   ├── app/
│   │   ├── core/               # Deterministic Request Analyzer (NLP)
│   │   ├── execution/          # Cache, Cost Engine, Guardrail, Fallback, Providers
│   │   │   └── providers/      # Gemini, Groq, OpenAI, Ollama, Simulation
│   │   ├── finops/             # Autonomous FinOps Advisor & What-If Simulator
│   │   └── routing/            # Router, Policy Engine, Budget Engine, Copilot
│   ├── database/               # SQLAlchemy Models, Connection & Repositories
│   ├── config.py               # Application settings
│   ├── main.py                 # FastAPI Gateway & REST endpoints
│   ├── requirements.txt        # Backend dependencies
│   └── .env.example            # Environment variables template
├── frontend/
│   ├── src/                    # React 19 Single Page App & Dashboards
│   ├── package.json            # Frontend dependencies
│   ├── vite.config.ts          # Reverse proxy to backend port 8001
│   └── tailwind.config.js
├── docs/                       # Architecture diagrams & specifications
├── scripts/                    # Windows batch / PowerShell launch scripts
├── tests/                      # Automated test suites
├── test_phase13_scenarios.py   # Live LLM validation script
├── .gitignore                  # Git ignore rules (secrets & binaries excluded)
└── README.md
```

---

## ⚡ Getting Started

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Node.js 18+ (Tested on Node.js 24)
- (Optional) Free API key from [Google AI Studio](https://aistudio.google.com/) or [Groq Console](https://console.groq.com/)

### 2. Configure Environment
Create `backend/.env` (copy from `backend/.env.example`):
```ini
APP_MODE=real
GEMINI_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
```
*(If no API keys are provided, set `APP_MODE=demo` to use the deterministic simulation provider).*

### 3. Start Backend
```bash
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```
Interactive API Documentation: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Web Application: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 🧪 Running Automated Tests

Run the backend test suite:
```bash
python -m pytest tests/
```

Run end-to-end live LLM validation:
```bash
python test_phase13_scenarios.py
```

---

## 📄 License
MIT License.
