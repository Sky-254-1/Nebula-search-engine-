<div align="center">

# Nebula Search Engine

**Private · Online & Offline-First · AI-Powered · Hybrid Search**

[![License: MIT](https://img.shields.io/badge/License-MIT-7c5cfc.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=white)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![Node](https://img.shields.io/badge/Node-20-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8.svg?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps)
[![Tests](https://img.shields.io/badge/Tests-pytest%20%7C%20Playwright-0A9EDC.svg)](https://playwright.dev)
[![PRs](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](docs/CONTRIBUTING.md)

A modern search platform combining web search, offline document search, AI-powered answers, and encrypted P2P sharing — with a privacy-first approach and zero tracking.

[Getting Started](docs/SETUP.md) · [Architecture](docs/ARCHITECTURE.md) · [API Docs](docs/API.md) · [Deployment](docs/DEPLOYMENT.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](docs/CONTRIBUTING.md)

</div>

---

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

- React app: http://localhost:5173
- API docs: http://localhost:8000/docs
- Legacy UI: http://localhost:5173/legacy/index.html

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Docker Support](#docker-support)
- [Testing Guide](#testing-guide)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)
- [Security](#security)

---

## Features

| Category | Features |
|----------|----------|
| :mag: Web Search | Wikipedia, Brave Search, SerpAPI backends — parallel orchestration with deduplication & ranking |
| :floppy_disk: Offline Search | TF-IDF and semantic ranking in the browser via IndexedDB |
| :robot: AI Answers | OpenAI-compatible API with automatic failover (OpenAI → Ollama → GGUF → DuckDuckGo) |
| :lock: Authentication | Email/password signup, JWT access + refresh tokens, optional 2FA/TOTP, WebAuthn |
| :busts_in_silhouette: RBAC | Role-based access control (user/admin tiers), rate limit tiers |
| :shower: Streaming | Server-Sent Events for AI answer streaming |
| :bar_chart: Vector Search | Hybrid keyword + semantic search with document indexing pipeline |
| :file_folder: Document Storage | Upload, manage, and search documents (.txt, .md, .pdf, .docx, .html, .json, .csv) |
| :globe_with_meridians: PWA | Installable progressive web app with service worker offline support |
| :hand: Privacy | Private mode, local caching, no telemetry, zero tracking |
| :mobile_phone_off: Offline-First | Full offline capabilities with local search and cached results |
| :iphone: Mobile | Capacitor-powered mobile shell (Android/iOS) |
| :test_tube: E2E Testing | Playwright E2E suite covering auth, search, AI, offline, documents |
| :observability: Observability | OpenTelemetry, Prometheus metrics, Sentry error tracking, structured logging |
| :shield: Security | CSP headers, HSTS, rate limiting, brute-force protection, audit logging, cookie-based auth |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite + React Router 6 | Single-page application |
| **Styling** | Vanilla CSS + PWA manifest | Lightweight, no framework lock-in |
| **Backend** | Python 3.11+ / FastAPI + Uvicorn | REST API with async support |
| **Database** | SQLite (dev), PostgreSQL 16 (prod) | Primary data store |
| **Vector DB** | pgvector / FAISS / JSON fallback | Embedding storage & similarity search |
| **Cache** | Redis 7 (in-memory fallback) | Caching, rate limiting, job queues |
| **AI** | OpenAI, Ollama, GGUF, DuckDuckGo | AI answer generation |
| **Search** | Wikipedia API, Brave Search, SerpAPI | External search providers |
| **Auth** | JWT (HS256) + PBKDF2-SHA256 | Authentication & session management |
| **ORM** | SQLAlchemy 2.0 + Alembic | Database schema & migrations |
| **Container** | Docker + Docker Compose | Local & production deployment |
| **Orchestrator** | Kubernetes (manifests provided) | Production scaling |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Mobile** | Capacitor (Android/iOS) | Mobile app shell |
| **Monitoring** | Prometheus, Grafana, Loki, OpenTelemetry | Observability stack |
| **Testing** | pytest, Playwright, pytest-cov | Unit, integration, E2E tests |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                              │
│  ┌───────────┐  ┌───────────┐  ┌─────────────────────────┐ │
│  │ React PWA │  │ Legacy UI │  │   Service Worker         │ │
│  │ (Vite v1) │  │ (HTML/JS) │  │   (offline cache + sync) │ │
│  └─────┬─────┘  └─────┬─────┘  └──────────┬──────────────┘ │
└────────┼───────────────┼───────────────────┼────────────────┘
         │               │                   │
         ▼               ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx Reverse Proxy                       │
│              TLS termination · Static serving                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ ┌────────┐ │
│  │ Routes │ │ Services │ │ Middleware│ │Caching│ │ Queue  │ │
│  └───┬────┘ └────┬─────┘ └────┬─────┘ └───┬───┘ └───┬────┘ │
│      │           │            │            │          │      │
│  ┌───▼───────────▼────────────▼────────────▼──────────▼───┐ │
│  │              DI Container & App Factory                 │ │
│  └─────────────────────────┬──────────────────────────────┘ │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│         ┌──────────────────▼──────────────────┐             │
│         │        External Providers            │             │
│         │  ┌────────┐ ┌───────┐ ┌──────────┐  │             │
│         │  │Wikipedia│ │ Brave│ │ SerpAPI   │  │             │
│         │  └────────┘ └───────┘ └──────────┘  │             │
│         │  ┌────────┐ ┌───────┐ ┌──────────┐  │             │
│         │  │ OpenAI  │ │Ollama │ │  GGUF    │  │             │
│         │  └────────┘ └───────┘ └──────────┘  │             │
│         │  ┌──────────┐                       │             │
│         │  │DuckDuckGo │ (fallback)           │             │
│         │  └──────────┘                       │             │
│         └─────────────────────────────────────┘             │
│                                                             │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────┐  │
│  │ PostgreSQL │  │   Redis    │  │   File Storage        │  │
│  │  (primary) │  │ (cache/q)  │  │  uploads/cache/vector  │  │
│  └────────────┘  └────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
nebula-search-engine/
├── .github/workflows/          # CI/CD workflows
│   ├── ci.yml                  # Backend tests + frontend build + E2E
│   └── codeql.yml              # CodeQL security analysis
├── backend/
│   ├── app/
│   │   ├── alembic/            # Alembic migration scripts
│   │   ├── config.py           # Environment settings (dataclass)
│   │   ├── database/           # Engine, repos, migrations
│   │   │   ├── engine.py       # SQLite + PostgreSQL adapter
│   │   │   ├── migrate.py      # SQL migration runner
│   │   │   ├── models.py       # SQLAlchemy ORM models (18 tables)
│   │   │   └── repositories/   # Data access layer (9 repos)
│   │   ├── main.py             # App factory, middleware, lifespan
│   │   ├── middleware/
│   │   │   ├── rate_limit.py   # Redis/in-memory + slowapi + tiers
│   │   │   └── security.py     # CSP, HSTS, security headers
│   │   ├── models/schemas.py   # Pydantic request/response models
│   │   ├── providers/ai/       # AI provider implementations
│   │   │   ├── base.py         # Abstract provider
│   │   │   ├── router.py       # Provider failover router
│   │   │   ├── openai.py       # OpenAI-compatible
│   │   │   ├── ollama.py       # Local Ollama
│   │   │   ├── gguf.py         # Local GGUF models
│   │   │   └── duckduckgo.py   # DuckDuckGo fallback
│   │   ├── routes/             # API route handlers
│   │   │   ├── auth.py, search.py, ai.py
│   │   │   ├── storage.py, vector.py
│   │   │   ├── admin.py, health.py
│   │   └── services/
│   │       ├── auth.py         # JWT, password hashing, brute-force
│   │       ├── search.py       # Web search providers
│   │       ├── ai.py           # AI completion + streaming
│   │       ├── cache.py        # Redis + in-memory cache
│   │       └── queue.py        # Background job queue
│   ├── vector/                 # Vector indexing pipeline (v1.1)
│   │   ├── ingestion/          # PDF, TXT, MD, DOCX, HTML extractors
│   │   ├── chunking/           # Text chunking strategies
│   │   ├── embeddings/         # Embedding generation
│   │   ├── storage/            # Vector storage
│   │   ├── retrieval/          # Vector search retrieval
│   │   ├── ranking/            # Hybrid ranking
│   │   ├── citations/          # Citation tracking
│   │   ├── pipeline/           # Index pipeline coordination
│   │   └── worker.py           # Background indexing worker
│   ├── .env.example
│   ├── requirements.txt        # Production deps
│   └── requirements-dev.txt    # + pytest, pytest-cov, pytest-asyncio
├── frontend/
│   ├── public/                 # PWA manifest, service worker, icons
│   ├── src/
│   │   ├── api/                # API client modules
│   │   │   ├── base.js         # Shared authedFetch
│   │   │   ├── auth.js, search.js, ai.js
│   │   │   └── client.js       # Facade
│   │   ├── auth/               # Auth context & guards
│   │   ├── components/         # Reusable UI components (9)
│   │   ├── hooks/              # Custom hooks (4)
│   │   ├── pages/              # Route pages
│   │   ├── state/              # SearchContext
│   │   ├── styles/
│   │   └── utils/
│   ├── legacy/                 # Original monolithic HTML UI
│   ├── package.json
│   └── vite.config.js
├── mobile/                     # Capacitor mobile shell (v1.1)
│   ├── android/, ios/
│   ├── src/                    # Mobile app source
│   ├── plugins/                # Native plugins
│   ├── sync/                   # Offline sync queue
│   └── capacitor.config.ts
├── docker/
│   ├── docker-compose.yml      # Full stack (Postgres, Redis, backend, frontend, worker)
│   ├── docker-compose.prod.yml # Production overrides
│   ├── Dockerfile              # Backend container
│   ├── frontend.Dockerfile     # Frontend container
│   └── nginx.conf
├── infrastructure/
│   ├── k8s/                    # Kubernetes manifests (18 files)
│   └── monitoring/             # Prometheus, Grafana, Loki, Alertmanager
├── tests/
│   ├── e2e/                    # Playwright E2E tests
│   │   ├── auth/, search/, ai/, offline/, mobile/, documents/, errors/
│   │   ├── fixtures/, utils/, config/
│   │   └── playwright.config.ts
│   ├── conftest.py
│   └── test_*.py               # pytest suite (19 test files)
├── storage/                    # Runtime data volumes
│   ├── uploads/, cache/, vector/, indexes/, exports/
├── scripts/                    # Dev helper scripts
│   ├── run-dev.sh, run-dev.ps1
├── deploy/                     # Production deployment guide
├── docs/                       # Documentation
├── package.json                # Root scripts (E2E, vector, mobile)
├── LICENSE                     # MIT
└── CHANGELOG.md                # Release history
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional, for containerized setup)

### Installation

```bash
# Clone the repository
git clone https://github.com/Sky-254-1/Nebula-search-engine-.git
cd Nebula-search-engine-

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env — set at minimum JWT_SECRET

# Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 for the React app, or http://localhost:8000/docs for interactive API docs.

### Configuration

All configuration is done via environment variables. See [docs/SETUP.md](docs/SETUP.md) for the complete reference.

**Minimum required for production:**
| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Strong random secret (32+ chars) |
| `CORS_ORIGINS` | Restricted to your frontend domain |
| `APP_ENV` | Set to `production` |

**Optional but recommended:**
- `OPENAI_API_KEY` — AI answers
- `BRAVE_API_KEY` or `SERPAPI_KEY` — paid search backends
- `DATABASE_URL` — PostgreSQL connection string

---

## Docker Support

```bash
cd docker

# Development (full stack with defaults)
docker compose up --build

# Production (with resource limits)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## Testing Guide

```bash
# Backend unit/integration tests (with coverage)
cd backend
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# E2E tests (Playwright)
# Start backend + frontend first, then:
npm run e2e:install     # First time only (installs Chromium)
npm run e2e             # Headless run
npm run e2e:headed      # Visible browser
npm run e2e:ui          # Playwright UI mode

# View E2E report
npm run e2e:report
```

**Test structure:**
| Layer | Tool | Coverage Target |
|-------|------|----------------|
| Unit | pytest (19 test files) | Auth, orchestrator, providers, cache |
| Integration | httpx ASGI | All API routes |
| Storage | pytest | Upload, settings, exports |
| E2E | Playwright | Auth, search, AI, offline, documents, errors, mobile |
| CI | GitHub Actions | Backend ≥75%, frontend build pass, E2E pass |

---

## API Documentation

Full API reference: [docs/API.md](docs/API.md)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | System health check |
| POST | `/api/v1/auth/signup` | No | Register new user |
| POST | `/api/v1/auth/login` | No | Sign in |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| POST | `/api/v1/auth/logout` | No | Revoke session |
| GET | `/api/v1/auth/me` | Yes | Current user profile |
| GET | `/api/v1/search/web` | Yes | Single-backend web search |
| GET | `/api/v1/search/orchestrate` | Yes | Multi-backend orchestrated search |
| GET | `/api/v1/search/history` | Yes | User search history |
| POST | `/api/v1/ai/ask` | Yes | AI answer |
| POST | `/api/v1/ai/ask/stream` | Yes | SSE streaming AI answer |
| GET | `/api/v1/ai/chat/history` | Yes | Chat history |
| POST | `/api/v1/ai/synthesize` | Yes | Synthesize search snippets |
| GET | `/api/v1/storage/documents` | Yes | List documents |
| POST | `/api/v1/storage/documents` | Yes | Upload document |
| DELETE | `/api/v1/storage/documents/{id}` | Yes | Delete document |
| GET | `/api/v1/storage/settings` | Yes | User settings |
| PUT | `/api/v1/storage/settings` | Yes | Update settings |
| POST | `/api/v1/storage/exports` | Yes | Create export job |
| GET | `/api/v1/storage/exports` | Yes | List exports |
| GET | `/api/v1/vector/search` | Yes | Hybrid vector + keyword search |
| POST | `/api/v1/vector/documents/{id}/reindex` | Yes | Queue document reindex |
| GET | `/api/v1/vector/citations` | Yes | Citation log |
| GET | `/api/v1/admin/audit-logs` | Admin | System audit logs |
| POST | `/api/v1/admin/users/{id}/role` | Admin | Update user role |

Interactive API docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md).

- Report bugs via [GitHub Issues](https://github.com/Sky-254-1/Nebula-search-engine-/issues)
- Submit pull requests following the PR template
- Adhere to existing code style and test coverage standards
- All PRs require passing CI checks (tests + frontend build + E2E)

---

## License

MIT License. Copyright (c) 2026 Sky-254-1. See [LICENSE](LICENSE) for full text.

---

## Security

Please see our [Security Policy](docs/SECURITY.md) for:
- Supported versions
- Vulnerability reporting process
- Security hardening checklist
- Authentication & authorization details
- Encryption & data protection
- API security measures
