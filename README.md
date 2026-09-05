# CodeIntel — GitHub Repository Intelligence & Codebase Copilot

CodeIntel is an AI/ML platform designed to ingest public GitHub repositories, perform deep structural analysis (AST / Tree-sitter), construct module dependency graphs, triage issues with machine learning classification models, and provide a grounded, citation-backed codebase Q&A experience.

---

## Architecture Overview

```
GitHub Repository
   └─► Repository Ingestion & Parsing (AST / Tree-sitter)
         ├─► Structural Code Chunker
         ├─► NetworkX Dependency Graph
         ├─► Hybrid Vector Search (BM25 + ChromaDB + Cross-Encoder Reranker)
         └─► ML Classification Pipeline (Issue Type, Severity, Duplicates, Risk)
```

---

## Project Structure

```text
Codeintel/
├── backend/                  # FastAPI Python backend (Clean Architecture)
│   ├── app/
│   │   ├── api/              # Presentation layer & FastAPI endpoints
│   │   ├── core/             # Configuration, logging, exception handlers, Redis pool
│   │   ├── models/           # SQLAlchemy ORM models (Repository, File, Issue, etc.)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Application service layer
│   │   ├── repositories/     # Database access layer
│   │   ├── ingestion/        # Repository ingestion pipeline stubs
│   │   ├── parsing/          # Code parsing & AST stubs
│   │   ├── rag/              # Hybrid RAG retrieval pipeline stubs
│   │   ├── ml/               # Machine Learning classification models stubs
│   │   ├── llm/              # LLM provider abstraction stubs
│   │   ├── graph/            # Dependency graph stubs
│   │   ├── workers/          # Background queue workers stubs
│   │   └── evaluation/       # RAG & ML evaluation metrics stubs
│   ├── alembic/              # Database migration scripts
│   ├── tests/                # Unit & integration tests (pytest)
│   └── Dockerfile
│
├── frontend/                 # Vite + React + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/       # Shared UI components
│   │   ├── pages/            # Page components (Home, Dashboard)
│   │   ├── layouts/          # Root layout & navigation
│   │   ├── hooks/            # Custom React hooks (useHealth, etc.)
│   │   ├── services/         # Axios API service calls
│   │   ├── types/            # TypeScript interfaces
│   │   ├── lib/              # Axios client config
│   │   └── stores/           # Zustand global state management
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker-compose.yml        # Orchestrates Postgres, Redis, ChromaDB, Backend, Frontend
├── .env.example              # Environment variables template
└── README.md
```

---

## Quick Start (Docker Compose)

### 1. Clone & Setup Environment
```bash
cp .env.example .env
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```

### 3. Access Services
- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **Backend Readiness Check:** [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

---

## Local Development (Without Docker)

### Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e .[all]
pytest tests/
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Health Check API Endpoints

- `GET /api/v1/health` — Liveness probe (returns service version and status)
- `GET /api/v1/health/ready` — Readiness probe (verifies PostgreSQL & Redis connections)
