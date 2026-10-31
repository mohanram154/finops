# NEXUS AI FINOPS — Setup Guide

## Prerequisites
- **Python**: 3.10+ (Detected: Python 3.14.3)
- **Node.js**: 18+ (Detected: Node v24.13.1, npm 11.8.0)

## Quick Start

### 1. Backend Setup
```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Start backend server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Backend will be live at `http://127.0.0.1:8000`.
- Health check: `http://127.0.0.1:8000/api/v1/health`
- Swagger Interactive Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Frontend will be live at `http://localhost:5173`.

### 3. Running Tests
```bash
python -m pytest tests/
```

