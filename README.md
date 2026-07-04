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

A modern search platform combining web search, offline document search, AI-powered answers, and encrypted P2P sharing — with a privacy-first approach and zero tracking.

[Getting Started](#quick-start) · [Architecture](#architecture) · [API Docs](docs/API.md) · [Deployment](docs/DEPLOYMENT.md) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md)

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
│  │ Routes │ │ Services │ │Middleware│ │Caching│ │ Queue  │ │
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
│   ├── vector/                 # Vector indexing pipeline
│   │   ├── ingestion/          # PDF, TXT, MD, DOCX, HTML extractors
│   │   ├── chunking/           # Text chunking strategies
│   │   ├── embeddings/         # Embedding generation
│   │   └── storage/            # Vector storage
│   ├── requirements.txt        # Python dependencies
│   └── alembic/                # Database migrations
├── frontend/
│   ├── src/                    # React + Vite app
│   ├── public/                 # PWA manifest + service worker
│   └── package.json
├── mobile/                     # Capacitor (Android/iOS)
├── database/                   # Database migrations & seeds
├── docker/                     # Docker Compose & configs
├── docs/                       # Documentation
├── tests/                      # Unit, integration, E2E tests
├── scripts/                    # Build, deploy scripts
├── deployment/                 # Kubernetes, Terraform, Ansible
├── storage/                    # uploads, cache, vector, indexes
└── .github/
    └── workflows/              # CI/CD pipelines
```

---

## Getting Started

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Sky-254-1/Nebula-search-engine-.git
   cd Nebula-search-engine-
   ```

2. **Backend setup:**
   ```bash
   cd backend
   pip install -r requirements-dev.txt
   cp .env.example .env
   # Edit .env and set JWT_SECRET
   uvicorn app.main:app --reload
   ```

3. **Frontend setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Verify:**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000/docs

### Docker (All-in-one)

```bash
cd docker
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Support

Full stack included:
- PostgreSQL 16
- Redis 7
- FastAPI backend
- React frontend
- Nginx reverse proxy

```bash
cd docker
docker compose -f docker-compose.yml up --build
```

---

## Testing Guide

### Unit Tests

```bash
cd backend
pytest tests/unit/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### E2E Tests (Playwright)

```bash
cd frontend
npm run e2e
```

### Coverage Report

```bash
pytest --cov=app --cov-report=html
```

---

## API Documentation

**Automatic documentation:** http://localhost:8000/docs (Swagger UI)

Key endpoints:

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| POST | `/api/v1/auth/signup` | Register | No |
| POST | `/api/v1/auth/login` | Login | No |
| GET | `/api/v1/auth/me` | Current user | Yes |
| GET | `/api/v1/search/web` | Web search | Yes |
| POST | `/api/v1/ai/ask` | AI answer | Yes |
| GET | `/metrics` | Prometheus metrics | No |

---

## Environment Variables

See `.env.example` for complete list. Critical variables:

```env
# Core
APP_ENV=production
JWT_SECRET=<strong-random-key>
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Search & AI
OPENAI_API_KEY=<your-key>
BRAVE_API_KEY=<your-key>
SERPAPI_KEY=<your-key>

# Security
CORS_ORIGINS=https://your-domain.com
ENABLE_CSRF=true
ENABLE_2FA=false
MAX_LOGIN_ATTEMPTS=5

# Observability
SENTRY_DSN=<your-sentry-dsn>
OTEL_EXPORTER_OTLP_ENDPOINT=<your-otel-endpoint>
LOG_LEVEL=INFO
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License · Copyright (c) 2026 Sky-254-1

---

## Security

For security issues, see [SECURITY.md](SECURITY.md)

---

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features and releases.

---

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/Sky-254-1/Nebula-search-engine-/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Sky-254-1/Nebula-search-engine-/discussions)
