<div align="center">

# Nebula Search

**Private · Online and Offline-First · AI-Powered · Hybrid Search Engine**

[![License: MIT](https://img.shields.io/badge/License-MIT-7c5cfc.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)

A modern search platform combining web search, offline document search, AI-powered answers, and encrypted P2P sharing — with a privacy-first approach and zero tracking.

[Getting Started](docs/SETUP.md) · [Architecture](docs/ARCHITECTURE.md) · [Deployment](docs/DEPLOYMENT.md) · [Roadmap](docs/ROADMAP.md)

</div>

---

## Features

- **Web Search** — Wikipedia, Brave Search, or SerpAPI backends
- **Offline Search** — TF-IDF and semantic ranking in the browser
- **AI Answers** — OpenAI-compatible API with DuckDuckGo fallback
- **Authentication** — Email/password signup with JWT tokens
- **Privacy** — Private mode, local caching, no telemetry
- **PWA** — Installable progressive web app

## Project Structure

```
Nebula-search-engine-/
├── frontend/
│   ├── src/               # React + Vite app (v1.0)
│   ├── public/            # PWA manifest + service worker
│   └── legacy/            # Original monolithic UI (full offline features)
├── backend/app/
│   ├── database/          # Engine, migrations, repositories
│   ├── providers/ai/      # OpenAI, Ollama, DuckDuckGo
│   ├── search/            # Search orchestrator
│   ├── routes/            # API endpoints
│   └── services/          # cache, auth, ai
├── tests/                 # 34 pytest tests
├── docs/                  # Architecture, implementation plan, mobile
├── docker/                # Full stack: Postgres, Redis, backend, frontend
└── storage/               # uploads, cache, vector, indexes, exports
```

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload

# Frontend (React)
cd frontend && npm install && npm run dev
```

- React app: http://localhost:5173
- Legacy UI: http://localhost:5173/legacy/index.html
- API docs: http://localhost:8000/docs

## Docker

```bash
cd docker
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/health` | Health check | No |
| POST | `/api/v1/auth/signup` | Register | No |
| POST | `/api/v1/auth/login` | Login | No |
| GET | `/api/v1/auth/me` | Current user | Yes |
| GET | `/api/v1/search/web` | Web search | Yes |
| POST | `/api/v1/ai/ask` | AI answer | Yes |
| POST | `/api/v1/ai/synthesize` | Synthesize snippets | Yes |

## Testing

```bash
cd backend
pytest --cov=app --cov-report=term-missing

# E2E (Playwright v1.1)
npm install && npm run e2e:install
npm run e2e
```

## Environment Variables

See [docs/SETUP.md](docs/SETUP.md) for the full list. Minimum for production:

- `JWT_SECRET` — required
- `CORS_ORIGINS` — restrict to your frontend domain
- `OPENAI_API_KEY`, `BRAVE_API_KEY`, `SERPAPI_KEY` — optional

## License

MIT License · Copyright (c) 2026 Sky-254-1
