# Nebula Search Engine — Architecture Audit

## Overview
Current architecture follows a monolithic layout with service-oriented structure inside a single FastAPI application. The frontend is a single-page React app with Vite.

## Current Architecture

```
frontend/ (React + Vite)
  └── proxies /api → backend:8000
backend/ (FastAPI)
  ├── app/
  │   ├── routes/        → API endpoints (auth, search, ai, storage, admin, vector, health)
  │   ├── services/      → Business logic (auth, ai, cache, queue, search)
  │   ├── middleware/    → Security headers, rate limiting
  │   ├── database/      → Engine, migrations, repositories
  │   ├── providers/     → AI provider routing
  │   ├── search/        → Search orchestrator
  │   └── models/        → Pydantic schemas
  ├── vector/            → Vector pipeline (chunking, embeddings, retrieval, ranking)
  └── tests/             → Pytest tests
docker/ (Docker Compose)
  ├── postgres:16
  ├── redis:7
  ├── backend
  ├── frontend (nginx)
  └── vector-worker
mobile/ (Capacitor)
docs/
```

## Strengths
- Clean API versioning (`/api/v1/`)
- Repository pattern for database access
- Dependency injection via FastAPI `Depends()`
- Dual SQLite/PostgreSQL support
- Redis/memory cache abstraction
- JWT auth with refresh token rotation
- Audit logging
- Search orchestration with parallel backends
- Vector pipeline for hybrid search
- Docker Compose for full stack

## Weaknesses
- No formal API Gateway layer
- No service layer separation — routes directly call repositories
- No dependency injection container (manual wiring)
- No event bus / message broker abstraction
- No health check per dependency (DB, Redis, AI providers)
- No OpenTelemetry instrumentation
- No circuit breaker for external service calls
- Monolithic backend — not yet microservice-ready
- No formal caching strategy beyond TTL-based
- No rate limiting per user tier
- No request validation middleware
- No formal error taxonomy

## Findings

| Issue | Severity | Impact | Recommendation |
|-------|----------|--------|----------------|
| Routes call repositories directly | Medium | Tight coupling | Add service layer |
| No API Gateway | Medium | No central auth/rate-limit | Add gateway |
| No event bus | Low | Sync-only operations | Add message queue |
| No circuit breakers | Medium | Cascading failures | Add resilience patterns |
| No OpenTelemetry | High | No observability | Add OTEL instrumentation |

## Remediation Plan
1. Add service layer between routes and repositories
2. Implement API Gateway pattern
3. Add event bus abstraction
4. Add circuit breakers and retries
5. Add OpenTelemetry instrumentation
6. Extract microservices along domain boundaries
