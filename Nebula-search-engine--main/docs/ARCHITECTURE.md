# Nebula Search Engine — Architecture

## System Architecture Overview

Nebula Search is a privacy-first hybrid search platform with a React frontend and a FastAPI backend. The frontend runs primarily in the browser with IndexedDB for offline storage; the backend provides authenticated web search, AI answers, document management, vector search, and search logging.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                             CLIENT LAYER                                 │
│                                                                            │
│  ┌─────────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │   React PWA (Vite)  │  │  Legacy HTML UI  │  │   Capacitor Mobile   │  │
│  │                     │  │                  │  │   (Android / iOS)    │  │
│  │  ┌───────────────┐  │  │  /legacy/        │  │                      │  │
│  │  │  AuthContext   │  │  │  (preserved)     │  │  ┌────────────────┐ │  │
│  │  │  SearchContext │  │  └────────┬─────────┘  │  │  Native Plugins│ │  │
│  │  │  React Router  │  │           │            │  │  (camera,share)│ │  │
│  │  └───────┬───────┘  │           │            │  └────────────────┘ │  │
│  └──────────┼──────────┘           │            └──────────┬───────────┘  │
│             │                      │                       │              │
│  ┌──────────▼──────────────────────▼───────────────────────▼───────────┐  │
│  │                   Service Worker (offline cache + sync)              │  │
│  │                   PWA Manifest + Install Prompt                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          GATEWAY LAYER                                    │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                       Nginx Reverse Proxy                           │  │
│  │              TLS termination · Static file serving                   │  │
│  │              Rate limiting · Request buffering                      │  │
│  └─────────────────────────────────┬───────────────────────────────────┘  │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼──────────────────────────────────────┐
│                          APPLICATION LAYER                                │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Backend (Uvicorn)                        │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ │  │
│  │  │  Routes  │ │  Services  │ │Middleware│ │  Cache  │ │  Queue   │ │  │
│  │  │          │ │            │ │          │ │ Service │ │ Service  │ │  │
│  │  │ • auth   │ │ • auth     │ │ • rate   │ │         │ │          │ │  │
│  │  │ • search │ │ • search   │ │   limit  │ │ Redis / │ │ Redis /  │ │  │
│  │  │ • ai     │ │ • ai       │ │ • security│ │ in-     │ │ in-memory│ │  │
│  │  │ • storage│ │ • cache    │ │   headers│ │ memory  │ │ fallback │ │  │
│  │  │ • vector │ │ • queue    │ │ • CORS   │ │         │ │          │ │  │
│  │  │ • admin  │ │            │ │          │ │         │ │          │ │  │
│  │  │ • health │ │            │ │          │ │         │ │          │ │  │
│  │  └──────────┘ └────────────┘ └──────────┘ └─────────┘ └──────────┘ │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │  Search Orchestrator  ·  AI Provider Router  ·  Vector       │   │  │
│  │  │  Pipeline (ingestion → chunking → embedding → retrieval)     │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼──────────────────────────────────────┐
│  ┌────────────────────────────────▼───────────────────────────────────┐  │
│  │                      EXTERNAL PROVIDERS                              │  │
│  │                                                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │Wikipedia │ │  Brave   │ │ SerpAPI  │ │  OpenAI  │ │  Ollama  │  │  │
│  │  │ (public) │ │ (API key)│ │ (paid)   │ │ (API key)│ │ (local)  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────────┐                                      │  │
│  │  │   GGUF   │ │  DuckDuckGo  │  (AI fallback chain)                │  │
│  │  │ (local)  │ │ (no key)     │                                      │  │
│  │  └──────────┘ └──────────────┘                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────────┐ │  │
│  │     PostgreSQL     │  │       Redis         │  │    File Storage     │ │  │
│  │     (primary)      │  │   (cache / queue)   │  │ uploads/cache/vec-  │ │  │
│  │                    │  │                    │  │ tor/indexes/exports │ │  │
│  │  • Users & sessions│  │  • Search cache    │  │                     │ │  │
│  │  • Search logs     │  │  • AI response     │  │  • User documents   │ │  │
│  │  • Chat history    │  │    cache           │  │  • Vector indexes   │ │  │
│  │  • Documents       │  │  • Rate limit      │  │  • Export files     │ │  │
│  │  • Vector chunks   │  │  • Job queue       │  │  • Processed cache  │ │  │
│  │  • Audit logs      │  │  • Session cache   │  │                     │ │  │
│  │  • Settings        │  │                    │  │                     │ │  │
│  └────────────────────┘  └────────────────────┘  └─────────────────────┘ │  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Component Tree

```
App.jsx
├── AuthContext.Provider
│   └── SearchContext.Provider
│       └── BrowserRouter
│           ├── / → HomePage
│           │   ├── Header (search bar, auth button)
│           │   ├── AuthModal (login/signup)
│           │   ├── SearchBar
│           │   ├── ResultsList
│           │   │   └── Pagination
│           │   ├── ChatPanel (AI chat)
│           │   └── Toast (notifications)
│           ├── /history → HistoryPage (lazy loaded)
│           └── ProtectedRoute (wrapper for authed pages)
│               └── ...pages
├── ErrorBoundary
└── InstallPrompt (PWA install banner)
```

### State Management

| Context | Provider | State | Persistence |
|---------|----------|-------|-------------|
| `AuthContext` | `AuthContext.jsx` | user, tokens, login/logout/signup | localStorage + cookies |
| `SearchContext` | `SearchContext.jsx` | query, results, filters, history | localStorage + IndexedDB |

### API Layer Architecture

```
client.js (facade)
├── base.js — shared `authedFetch()` with token refresh interceptor
├── auth.js — signup, login, refresh, logout
├── search.js — web, orchestrate, history
└── ai.js — ask, stream, chat history, synthesize
```

The `authedFetch()` helper automatically attaches `Authorization: Bearer <token>` headers, handles 401 responses by attempting token refresh, and stores/retrieves tokens from localStorage.

### Key Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useSearch` | `hooks/useSearch.js` | Search state, pagination, backend switching |
| `useAI` | `hooks/useAI.js` | AI answer, streaming, synthesis |
| `useChat` | `hooks/useChat.js` | Chat history management |
| `useInstallPrompt` | `hooks/useInstallPrompt.js` | PWA install prompt handling |

---

## Backend Architecture

### Application Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│  ROUTES (presentation layer)                                │
│  • Validate HTTP request params & body via Pydantic         │
│  • Delegate to services                                     │
│  • Return responses                                         │
├─────────────────────────────────────────────────────────────┤
│  SERVICES (business logic layer)                            │
│  • Auth: password hashing, JWT creation/validation          │
│  • Search: provider dispatch, query sanitization            │
│  • AI: provider routing, caching, streaming                │
│  • Cache: Redis/in-memory abstraction                       │
│  • Queue: background job processing                         │
├─────────────────────────────────────────────────────────────┤
│  REPOSITORIES (data access layer)                           │
│  • User, Session, Query, SearchResult                       │
│  • Document, Chunk, Embedding, Citation                     │
│  • Chat, Settings, Export, AuditLog                         │
├─────────────────────────────────────────────────────────────┤
│  DATABASE ENGINE (database abstraction layer)               │
│  • SQLite (dev) / PostgreSQL (prod)                         │
│  • Adapter pattern: same interface for both                 │
│  • Connection pooling via asyncpg                           │
├─────────────────────────────────────────────────────────────┤
│  MIDDLEWARE (cross-cutting concerns)                        │
│  • Security headers (CSP, HSTS, XFO, COEP, COOP, CORP)     │
│  • Rate limiting (tier-based, burst, IP/scope)             │
│  • CORS                                                    │
│  • Error handling                                           │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Injection

The app uses FastAPI's `Depends()` for dependency injection:

```python
# Route example
@router.get("/search/web")
async def web_search(
    q: str = Query(...),
    email: str = Depends(get_current_user),  # Auth dependency
    db=Depends(get_db),                      # Database connection
):
    # email and db are injected automatically
    results = await run_web_search(q, ...)
```

Key dependencies:
- `get_current_user` — validates JWT, returns email
- `require_admin` — validates JWT + admin role
- `get_db` — provides database connection
- `rate_limit` — enforces rate limits
- `limit_signup` / `limit_login` / `limit_refresh` — auth-specific rate limits

### Middleware Pipeline

```
Request → CORSMiddleware → SecurityHeadersMiddleware → Router → Response
                                          │
                                          ▼
                              Headers added:
                              • X-Content-Type-Options: nosniff
                              • X-Frame-Options: DENY
                              • Referrer-Policy: strict-origin-when-cross-origin
                              • Permissions-Policy
                              • Content-Security-Policy
                              • Strict-Transport-Security (prod only)
                              • Cross-Origin-Embedder-Policy
                              • Cross-Origin-Opener-Policy
                              • Cross-Origin-Resource-Policy
```

---

## Database Architecture

### Schema Overview (18 tables)

```
users ──┬── sessions                    # JWT refresh token tracking
        ├── queries                     # Search queries
        ├── search_results              # Individual search results
        ├── chat_messages               # AI chat history
        ├── documents                   # Uploaded documents
        ├── chunks                      # Document chunks (vector pipeline)
        ├── embeddings                  # Vector embeddings
        ├── user_settings               # Per-user settings
        ├── exports                     # Export jobs
        ├── audit_logs                  # Security audit trail
        ├── notifications               # User notifications
        ├── analytics_events            # Usage analytics
        ├── saved_searches              # Saved search queries
        ├── collections                 # Document collections
        ├── collection_items            # Collection-document mapping
        ├── bookmarks                   # URL bookmarks
        ├── crawler_jobs                # Web crawler jobs
        └── crawled_pages               # Crawled page content

users ──┬── billing_subscriptions ──┬── billing_plans
```

### Key Relationships

- `users` 1:N `sessions`, `queries`, `chat_messages`, `documents`, `audit_logs`
- `users` 1:1 `user_settings`
- `documents` 1:N `chunks` 1:N `embeddings`
- `queries` 1:N `search_results`
- `collections` 1:N `collection_items`

### Database Adapter Pattern

The engine layer (`backend/app/database/engine.py`) provides an abstract `DatabaseConnection` with concrete implementations:

| Adapter | Driver | When Used |
|---------|--------|-----------|
| `SQLiteConnection` | `aiosqlite` | `DATABASE_URL` starts with `nebula.db` or a path |
| `PostgresConnection` | `asyncpg` | `DATABASE_URL` starts with `postgresql://` |

The adapter handles SQL placeholder translation (`?` → `$1, $2, ...`) transparently.

### Vector Storage

| Storage | When Used | Notes |
|---------|-----------|-------|
| pgvector | PostgreSQL | Native vector(1536) type with IVFFlat indexes |
| FAISS | Standalone | Optional for large-scale vector search |
| JSON | SQLite | Embeddings stored as JSON text fields |

### Migration Strategy

**Current:** SQL-based migrations in `backend/app/database/migrations/`:
- `001_*.sql` — Core schema (users, sessions, queries, search_results, chat_history)
- `002_*.sql` — Vector pipeline (chunks, embeddings, citations, search_sessions)
- `003_*.sql` — Extended schema (notifications, analytics, billing, crawler, bookmarks, collections)

**Future (v1.2+):** Alembic incremental migrations configured at `backend/alembic.ini`.

---

## Search Pipeline

```
Query → Sanitize → Expand → Parallel Fetch → Rank → Dedupe → Cache → Paginate → Response
```

### Detailed Flow

```
┌──────────┐    ┌───────────┐    ┌────────────────┐
│  Client  │───▶│  Route    │───▶│  Orchestrator  │
│  Request │    │  handler  │    │                 │
└──────────┘    └───────────┘    └────────┬────────┘
                                          │
                              ┌───────────▼───────────┐
                              │   Cache check          │
                              │   key: search:{hash}   │
                              └───────┬───────┬───────┘
                                      │       │
                                 cache hit  cache miss
                                      │       │
                                      │  ┌────▼────┐
                                      │  │ Expand  │
                                      │  │ Query   │
                                      │  └────┬────┘
                                      │       │
                                      │  ┌────▼──────────────┐
                                      │  │ Parallel Fetch     │
                                      │  │ ┌────┬────┬────┐  │
                                      │  │ │Wiki│Brave│SERP│  │
                                      │  │ └────┴────┴────┘  │
                                      │  └────┬──────────────┘
                                      │       │
                                      │  ┌────▼────┐
                                      │  │  Rank   │
                                      │  │  Dedupe │
                                      │  └────┬────┘
                                      │       │
                                      │  ┌────▼────┐
                                      │  │  Cache  │
                                      │  │  SET    │
                                      │  └────┬────┘
                                      │       │
                                      └───────┘
                                          │
                              ┌───────────▼───────────┐
                              │   Log to search_logs   │
                              └───────────────────────┘
```

### Search Providers

| Provider | Auth Required | Rate Limits | Quality |
|----------|-------------|-------------|---------|
| Wikipedia | None | Public API | Encyclopedic |
| Brave Search | API key | 2,000 req/mo free | General web |
| SerpAPI | API key | 100 req/mo free | Google results |

---

## AI Pipeline

```
Prompt → Cache Check → Router → Provider Fallback Chain → Response
```

### AI Router Fallback Order

The `AIProviderRouter` in `backend/app/providers/ai/router.py` implements a configurable priority chain:

```
Prompt
  │
  ▼
AI Router
  │
  ├── Priority 1: AI_PROVIDER setting (if set)
  │   ├── "openai"     → openai → ollama → gguf → duckduckgo
  │   ├── "ollama"     → ollama → gguf → openai → duckduckgo
  │   ├── "gguf"       → gguf → ollama → openai → duckduckgo
  │   └── "duckduckgo" → duckduckgo → openai → ollama → gguf
  │
  └── Auto mode (default):
      ├── OpenAI (if API key present)
      ├── Ollama (if reachable)
      ├── GGUF (if model path set)
      └── DuckDuckGo (always available, no key)
```

### Streaming Architecture

```
POST /api/v1/ai/ask/stream
  → SSE (text/event-stream)
  → Chunks yield as "data: {"chunk": "..."}\n\n"
  → Terminal: "data: [DONE]\n\n"
```

Streaming falls back through the same provider chain. If no provider supports streaming, the router falls back to `complete()` and yields the full response as a single chunk.

### AI Caching

- Key: `ai:{prompt[:200]}`
- TTL: Configurable via `CACHE_TTL_SECONDS` (default 300s)
- Cache is skipped when `use_cache=False` (not currently exposed via API)

---

## Vector Search Pipeline

```
Document Upload → Extract → Chunk → Embed → Store → Search
```

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Upload      │───▶│  Extract     │───▶│  Chunking    │
│  POST        │    │  Text from   │    │  Split into  │
│  /storage/   │    │  PDF/DOCX/   │    │  segments    │
│  documents   │    │  HTML/TXT/MD │    │              │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
                                   ┌──────────────────────┐
                                   │  Embedding Generation │
                                   │  • OpenAI (if key)     │
                                   │  • sentence-transform- │
                                   │    ers (local)         │
                                   └──────────┬───────────┘
                                              │
                                              ▼
                                   ┌──────────────────────┐
                                   │  Vector Storage       │
                                   │  • pgvector           │
                                   │  • JSON (SQLite)      │
                                   └──────────┬───────────┘
                                              │
                                              ▼
                                   ┌──────────────────────┐
                                   │  Hybrid Search        │
                                   │  • Vector similarity  │
                                   │  • Keyword (BM25)     │
                                   │  • Combined ranking   │
                                   └──────────────────────┘
```

### Supported Document Formats

`.txt`, `.md`, `.json`, `.csv`, `.pdf`, `.html`, `.htm`, `.docx`

---

## AI Answer Caching Architecture

```
          ┌─────────┐
          │ Request │
          └────┬────┘
               │
          ┌────▼────┐
          │ Cache   │
          │ Lookup  │
          └────┬────┘
               │
     ┌─────────┴──────────┐
     │                    │
   cache hit          cache miss
     │                    │
     ▼                    ▼
  Return              Route to
  cached              Provider
  answer                 │
                     ┌───▼───┐
                     │Cache  │
                     │Store  │
                     └───────┘
                         │
                         ▼
                     Return
                     answer
```

---

## Security Architecture

### Authentication Flow

```
┌─────────┐     ┌──────────┐     ┌────────────┐
│  Client │     │  FastAPI │     │  Database  │
└────┬────┘     └────┬─────┘     └──────┬─────┘
     │                │                  │
     │ POST /login    │                  │
     │ {email, pass}  │                  │
     ├───────────────▶│                  │
     │                │── get_user() ──▶│
     │                │◀─ user row ─────│
     │                │                  │
     │                │ verify_password()
     │                │                  │
     │                │── create_session ─▶
     │                │  (hash refresh)  │
     │                │                  │
     │◀─ access_token │                  │
     │   refresh_token│                  │
     │   (or cookies) │                  │
     │                │                  │
     │ GET /search    │                  │
     │ Authorization: │                  │
     │ Bearer <token> │                  │
     ├───────────────▶│                  │
     │                │ decode_token()
     │◀─── results ──│                  │
```

### Password Security

- Algorithm: PBKDF2-SHA256 with 200,000 iterations
- Per-password random 16-byte salt (hex-encoded)
- Format: `{salt}${hash}`
- Password policy: 8-128 chars, upper + lower + digit + special, no common passwords

### JWT Tokens

| Token | Type | Lifetime | Storage |
|-------|------|----------|---------|
| Access | JWT (HS256) | 24h (configurable) | Memory / HTTP-only cookie |
| Refresh | Random URL-safe token | 30d (configurable) | HTTP-only cookie / request body |

### RBAC

Roles: `user` (default), `admin`

| Role | Permissions |
|------|-------------|
| `user` | Search, AI, storage, vector, own history |
| `admin` | All user permissions + audit logs, session management, role management |

Rate limit tiers are also role-based:
| Tier | Requests/min |
|------|-------------|
| `basic` (default user) | 30 |
| `pro` | 120 |
| `enterprise` | 600 |

### Brute-Force Protection

- Per-IP+email attempt tracking (3600s TTL)
- Lockout after `MAX_LOGIN_ATTEMPTS` (default: 5)
- Lockout duration: `LOGIN_LOCKOUT_MINUTES` (default: 15)
- Exponential delay: 1, 2, 4, 8, 15 seconds

### Audit Logging

All security-sensitive operations are logged:
- Signup, login, logout (per-session)
- Token refresh (with session family tracking)
- Refresh token reuse detection (security alerts)
- Admin actions (role changes, session revocation)
- Retention: 90 days (auto-cleanup)

---

## Observability Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Metrics Collection                     │
│                                                              │
│  FastAPI App ──▶ Prometheus Client ──▶ /metrics endpoint     │
│                        │                                     │
│                        ▼                                     │
│  OpenTelemetry SDK ──▶ OTLP Exporter ──▶ OpenTelemetry       │
│  (traces + metrics)                       Collector          │
│                                             │                │
│                      ┌──────────────────────┼─────────┐      │
│                      ▼                      ▼         ▼      │
│                  Prometheus              Loki     Grafana    │
│                  (metrics)              (logs)   (dashboards)│
│                      │                                      │
│                      ▼                                      │
│               Alertmanager → Pager/Email/Slack               │
└──────────────────────────────────────────────────────────────┘
```

### Logging

- JSON structured logs (configurable via `LOG_JSON_FORMAT`)
- Log levels: `DEBUG` (dev), `INFO` (prod) — configurable via `LOG_LEVEL`
- Sentry error tracking via `SENTRY_DSN`
- Audit logs persisted to database (90-day retention)

### Health Checks

`GET /health` returns:
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "environment": "production",
  "timestamp": "2026-06-30T12:00:00+00:00",
  "database": "postgresql",
  "cache": "redis"
}
```

---

## Deployment Architecture

### Docker Compose (Single Node)

```
┌────────────────────────────────────────────────────┐
│                     Docker Host                     │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Frontend │  │ Backend  │  │ Vector Worker    │  │
│  │ :3000    │  │ :8000    │  │ (background)     │  │
│  │ nginx    │  │ uvicorn  │  │                  │  │
│  └──────────┘  └────┬─────┘  └──────────────────┘  │
│                     │                               │
│  ┌──────────┐  ┌────▼─────┐  ┌──────────────────┐  │
│  │ Redis    │  │PostgreSQL│  │ Shared Volume    │  │
│  │ :6379    │  │ :5432    │  │ /app/storage     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────┘
```

### Kubernetes (Multi-Node)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Ingress    │  Ingress     │  Ingress    │  Ingress    │
│  Controller │  Controller  │  Controller │  Controller │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
       │              │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│  Frontend   │ │  Backend   │ │  Backend   │ │ Vector     │
│  Pod        │ │  Pod 1     │ │  Pod 2     │ │ Worker Pod │
└─────────────┘ └─────┬──────┘ └─────┬──────┘ └─────────────┘
                      │              │
┌─────────────────────┴──────────────┴──────────────────────┐
│                   PostgreSQL StatefulSet                    │
│                   Redis StatefulSet                        │
│                   Shared PVC (ReadWriteMany)               │
└────────────────────────────────────────────────────────────┘
```

### CI/CD Pipeline (GitHub Actions)

```
Push / PR → [test, frontend] → [e2e] → Deploy
  │            │          │         │
  │            ▼          ▼         ▼
  │        pytest     npm build  Playwright
  │        (3.11/     + lint     (Chromium)
  │        3.12)
  │
  ▼
CodeQL SAST (security scan)
```

---

## Data Flow Diagrams

### Full Search with AI Synthesis

```
User → React App → API Gateway → Backend → Cache → Providers → DB → Response
  │        │            │           │        │        │        │       │
  │  1. Type query     │           │        │        │        │       │
  ├───────────────────▶│           │        │        │        │       │
  │                    │  2. POST  │        │        │        │       │
  │                    │  /search/ │        │        │        │       │
  │                    │  orchestrate         │        │        │       │
  │                    ├──────────▶│        │        │        │       │
  │                    │           │  3. Cache check  │        │       │
  │                    │           ├───────▶│        │        │       │
  │                    │           │  miss  │        │        │       │
  │                    │           │  4. Parallel fetch    │        │       │
  │                    │           ├─────────────────────────▶        │       │
  │                    │           │  5. Rank + dedupe     │        │       │
  │                    │           │  6. Cache store       │        │       │
  │                    │           │  7. Log query         │───────▶│       │
  │                    │           │  8. Return results    │        │       │
  │                    │◀──────────├───────────────────────┤        │       │
  │ 9. Display results │           │                        │        │       │
  │◀───────────────────│           │                        │        │       │
  │                    │           │                        │        │       │
  │ 10. Request AI     │           │                        │        │       │
  │     synthesis      │           │                        │        │       │
  ├───────────────────▶│  11. POST │                        │        │       │
  │                    │  /ai/     │                        │        │       │
  │                    │  synthesize                       │        │       │
  │                    ├──────────▶│                        │        │       │
  │                    │           │  12. Route to AI      │        │       │
  │                    │           │      provider + cache  │        │       │
  │                    │           │  13. Log chat          │───────▶│       │
  │                    │           │  14. Return synthesis  │        │       │
  │                    │◀──────────├───────────────────────┤        │       │
  │ 15. Show synthesis │           │                        │        │       │
  │◀───────────────────│           │                        │        │       │
```

### Document Upload & Vector Indexing

```
User → POST /storage/documents → Queue → Worker → DB → Response
  │            │                    │        │       │       │
  │  1. Upload │                    │        │       │       │
  ├───────────▶│                    │        │       │       │
  │            │  2. Validate +     │        │       │       │
  │            │     store file     │        │       │       │
  │            │  3. Create doc     │        │       │       │
  │            │     record         │───────▶│       │       │
  │            │  4. Enqueue job    │        │       │       │
  │            ├───────────────────▶│        │       │       │
  │            │  5. Return ID      │        │       │       │
  │◀───────────┤                    │        │       │       │
  │            │                    │        │       │       │
  │  6. Poll   │                    │        │       │       │
  │  status    │                    │        │       │       │
  ├───────────▶│                    │        │       │       │
  │            │  7. Queue          │        │       │       │
  │            │     dequeue        │        │       │       │
  │            │◀─────────────────────────────│       │       │
  │            │                    │        │       │       │
  │            │                    │  8. Extract text      │
  │            │                    │  9. Chunk document    │
  │            │                    │ 10. Generate embedding│
  │            │                    │ 11. Store chunks      │───────▶│
  │            │                    │ 12. Store embeddings  │───────▶│
  │            │                    │ 13. Update doc status │───────▶│
  │            │  14. Status:      │        │       │       │
  │            │      "indexed"    │        │       │       │
  │◀───────────┤                    │        │       │       │
```

---

## Component Interaction Diagrams

### Auth Session Refresh Flow

```
Frontend                    Backend                         Database
   │                           │                              │
   │  GET /search (JWT)        │                              │
   ├──────────────────────────▶│                              │
   │                           │                              │
   │  401 Token Expired        │                              │
   │◀──────────────────────────│                              │
   │                           │                              │
   │  POST /auth/refresh       │                              │
   │  (refresh_token)          │                              │
   ├──────────────────────────▶│                              │
   │                           │  SELECT session by hash      │
   │                           ├─────────────────────────────▶│
   │                           │◀─────────────────────────────│
   │                           │                              │
   │                           │  Validate: not revoked,      │
   │                           │  not expired, not rotated    │
   │                           │                              │
   │                           │  UPDATE rotation timestamp   │
   │                           ├─────────────────────────────▶│
   │                           │                              │
   │                           │  INSERT new session (rotate) │
   │                           ├─────────────────────────────▶│
   │                           │                              │
   │  New access + refresh     │                              │
   │◀──────────────────────────│                              │
   │                           │                              │
   │  Retry GET /search        │                              │
   ├──────────────────────────▶│                              │
   │                           │                              │
   │  200 OK + results         │                              │
   │◀──────────────────────────│                              │
```

### AI Provider Failover Flow

```
Client                    AI Router              OpenAI    Ollama    GGUF      DuckDuckGo
  │                          │                     │        │        │         │
  │ POST /ai/ask             │                     │        │        │         │
  ├─────────────────────────▶│                     │        │        │         │
  │                          │                     │        │        │         │
  │                          │ 1. Try OpenAI        │        │        │         │
  │                          ├────────────────────▶│        │        │         │
  │                          │     Timeout/Error    │        │        │         │
  │                          │◀────────────────────│        │        │         │
  │                          │                     │        │        │         │
  │                          │ 2. Fallback Ollama  │        │        │         │
  │                          ├─────────────────────────────▶│        │         │
  │                          │     Response                 │        │         │
  │                          │◀─────────────────────────────│        │         │
  │                          │                     │        │        │         │
  │  AI response             │                     │        │        │         │
  │◀─────────────────────────│                     │        │        │         │
```

### Cache Flow

```
Client              Route              Cache Service              Redis / In-Memory
  │                    │                     │                        │
  │  Request           │                     │                        │
  ├───────────────────▶│                     │                        │
  │                    │  Cache check(key)    │                        │
  │                    ├────────────────────▶│                        │
  │                    │                     │  GET key                │
  │                    │                     ├───────────────────────▶│
  │                    │                     │◀───────────────────────│
  │                    │◀────────────────────│                        │
  │                    │                     │                        │
  │  ┌─── Cache hit ───┤                     │                        │
  │  │ Return cached   │                     │                        │
  │◀─┤                 │                     │                        │
  │  │                 │                     │                        │
  │  └─── Cache miss ──┤                     │                        │
  │                    │  Execute logic      │                        │
  │                    │  (search/AI/etc)    │                        │
  │                    │                     │                        │
  │                    │  Store in cache     │                        │
  │                    ├────────────────────▶│                        │
  │                    │                     │  SET key (TTL)         │
  │                    │                     ├───────────────────────▶│
  │                    │                     │                        │
  │                    │  Return fresh data  │                        │
  │◀───────────────────┤                     │                        │
```

---

## Rate Limiting Architecture

```
Request → IP/User Identification → Tier Resolution → Burst Check → Steady-State → Pass/Reject
                │                        │                │               │
                ▼                        ▼                ▼               ▼
          ┌─────────────┐         ┌─────────────┐  ┌────────────┐  ┌────────────┐
          │ IP from     │         │ role from   │  │ burst key  │  │ sliding    │
          │ request     │         │ JWT payload │  │ (2s window)│  │ window     │
          │ or user sub │         │             │  │            │  │ (60s)      │
          └─────────────┘         └─────────────┘  └────────────┘  └────────────┘
```

### Cache Key Patterns

| Pattern | TTL | Purpose |
|---------|-----|---------|
| `search:{hash}` | 300s | Orchestrated search results |
| `ai:{prompt_hash}` | 300s | AI answer cache |
| `session:{user_id}` | 86400s | Optional session hot cache |
| `ratelimit:{ip}:{path}` | 60s | Rate limit counters |
| `ratelimit:{user}:{path}` | 60s | Authenticated user limits |
| `burst:{key}` | 2s | Burst rate limit counters |
| `queue:jobs` | — | Background job list |
| `attempts:{ip}:{email}` | 3600s | Brute-force attempt tracking |
| `lockout:{ip}:{email}` | 900s | Brute-force lockout |

### Cache Invalidation

- TTL-based automatic expiration
- Manual prefix invalidation: `invalidate_prefix("search:")` on settings change
- In-memory fallback when Redis is unavailable (single-worker only)
- Redis fallback: graceful degradation, warning logged

---

## Storage Platform

| Directory | Content | Retention |
|-----------|---------|-----------|
| `storage/uploads/` | User-uploaded files | Until user deletes |
| `storage/cache/` | Processed document cache | 7 days TTL |
| `storage/vector/` | Embedding vectors | Per document |
| `storage/indexes/` | Full-text indexes | Rebuilt on upload |
| `storage/exports/` | Generated export files | 30 days |
