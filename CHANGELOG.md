# Changelog

All notable changes to Nebula Search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-08-03

### Added

- **Backend Tests** - 1358 tests (up from 477), 61% code coverage (up from 49%)
- **New API Domains**:
  - `auth_extended.py` - Extended authentication routes (pending email, email verification)
  - `notifications.py` - Real-time notifications system
  - `collections.py` - Collections management
  - `mfa.py` - MFA setup and management routes
  - `mobile.py` - Mobile-specific API endpoints
  - `analytics.py` - Analytics and reporting endpoints
  - `recommendations.py` - Personalized recommendations
  - `indexing.py` - Document indexing control endpoints
- **Security Hardening**:
  - CodeQL fixes: JWT secret logging, API key exposure, HTML parsing, CORS hardening, deploy.yml permissions
  - OAuth2 providers: Google, GitHub, Microsoft, Apple
  - WebAuthn support for passwordless auth
  - Least-privilege permissions in CI/CD workflows
- **Database Migrations** - 22+ idempotent migrations (Postgres + SQLite variants) with schema_migrations tracking
- **Hybrid Search** - Improved fusion algorithm with RRF + linear + adaptive fusion
- **Incremental Indexing** - Change detection and delta indexing support
- **Queue System** - Background job queue with retry logic
- **Crawler** - Async web crawler with depth control, rate limiting, robots.txt respect

### Changed

- **Pytest Configuration** - Fixed test collection: now only collects from `backend/tests/` (1408 tests)
- **Migration System** - Updated `migrate.py` with proper idempotency and SQLite/Postgres support
- **Vector Search** - Integrated `backend/vector/` module (faiss, bm25, fusion, semantic, embeddings)
- **Project Structure** - Consolidated duplicate directories: removed `infra/`, `database/migrations/` (root), root docker-compose files
- **Makefile** - Docker commands now reference `docker/` directory

### Fixed

- **Test Collection Errors** - Resolved `ModuleNotFoundError` from duplicate root tests directory
- **Pytest Configuration** - Updated `testpaths` to only include `backend/tests`
- **API Endpoints** - MFA router endpoints now accessible after routing fix
- **Storage Directories** - Consolidated `storage/indexes/` → `storage/index/`, `storage/vectors/` → removed

### Removed

- **Root Test Directory** - Removed 16 outdated test files from `tests/` (root)
- **Infrastructure Duplicates** - Deleted `infra/` directory
- **Docker Compose Duplicates** - Deleted 4 root docker-compose files
- **Database Migrations (root)** - Deleted 4 outdated migration files
- **Storage Directories** - Deleted `storage/indexes/`, `storage/vectors/`
- **Legacy Files** - Deleted `frontend/legacy/`, stale scripts, generated artifacts
- **Codeql Scaffolding** - Deleted `codeql-custom-queries-*/` directories
- **Figma MCP** - Deleted `Figma-Context-MCP/` (~30 unrelated files)
- **Environment Files** - Removed root `package.json`, `package-lock.json`

---

## [1.1.0] - 2026-07-28

### Added

- **Vector Search Pipeline** - Complete document indexing with text extraction
  - Supports PDF, DOCX, HTML, TXT, MD, JSON, CSV
  - Automatic text chunking (800 chars, 200 overlap)
  - Content hash deduplication
- **Citation Tracking** - Source attribution for search results
  - Track which chunks were cited in answers
  - APA/MLA/Chicago citation formatting helpers
- **Hybrid Search API** - `/api/v1/vector/*` endpoints
  - Document indexing: `POST /api/v1/vector/documents/{id}/index-now`
  - Vector search: `POST /api/v1/vector/search`
  - Citation listing: `GET /api/v1/vector/citations`
  - Export vectors: `POST /api/v1/vector/export`
- **Document Upload UI** - React components for document management
- **Mobile Capacitor Shell** - iOS/Android support
  - Camera, Filesystem, Network, Preferences plugins
  - Voice recognition integration
- **Background Worker** - `vector/worker.py` for async document processing
- **Migration 002** - Add document_chunks, embeddings, citations, search_sessions tables
- **MFA Support** - TOTP-based multi-factor authentication with backup codes
- **Database Migrations** - 22+ idempotent migrations (001-013) with SQLite/Postgres variants
- **Migration Idempotency** - `schema_migrations` tracking table prevents duplicate application
- **E2E Test Skip Guards** - Tests requiring external API keys now properly skip when keys are unset

### Changed

- **Search Orchestrator** - Improved result deduplication and ranking
- **AI Provider Router** - Better fallback logic for provider selection
- **Rate Limiting** - Path-specific rate limiting keys
- **Security Headers** - HSTS added for production environments
- **Migration Runner** - Now uses `schema_migrations` tracking table (standard Alembic-style pattern)
- **Postgres Migrations** - All `ALTER TABLE ADD COLUMN` use `IF NOT EXISTS`; all `CREATE INDEX` use `IF NOT EXISTS`
- **Vector Search Pipeline** - Fully integrated with FastAPI app via `backend/vector/` module

### Fixed

- **Security** - SQL injection in audit.py (placeholder substitution)
- **Session Management** - Session family revocation on logout
- **CORS Configuration** - Default localhost origins
- **Postgres Migration 003** - Missing MFA columns (`mfa_enabled`, `mfa_secret`, `mfa_backup_codes`) and auth columns now properly added
- **StopWordRemover** - `'StopWordRemover' object has no attribute 'remove'` crash in query pipeline (added missing `remove()` method)
- **npm Audit** - 5 moderate findings accepted as non-breaking (react-router SSR CVE does not apply to SPA; prismjs requires breaking upgrade)

### Security

- Added Content-Security-Policy headers
- Enhanced password policy enforcement
- Improved brute-force protection
- TOTP-based MFA with encrypted backup codes
- OAuth2 providers (Google, GitHub, Microsoft, Apple)
- CodeQL fixes for secret logging, API key exposure, HTML parsing, CORS, deploy permissions
- Least-privilege permissions in CI/CD workflows
- WebAuthn support for passwordless authentication
- CORS wildcard protection with explicit origin lists

---

## [1.0.0] - 2026-06-15

### Added

- **Backend API** - FastAPI with 7 routers, 41+ endpoints
- **Authentication** - JWT + refresh tokens with rotation
- **Search Backends** - Wikipedia, Brave Search, SerpAPI
- **AI Integration** - OpenAI, Ollama, GGUF, DuckDuckGo
- **Caching** - Redis + in-memory fallback
- **Docker Stack** - Full stack deployment (postgres, redis, backend, frontend)
- **Documentation** - 13 markdown files including API docs
- **Testing** - Pytest + Playwright E2E

### Security

- PBKDF2-SHA256 password hashing (200k iterations)
- Rate limiting with Redis
- Security headers middleware
- SQL injection prevention
- XSS protection via input validation

---

## [Unreleased] - v1.2.0 (Planned)

### Planned

- Biometric auth via `@capacitor-community/biometric`
- OpenAI embeddings as default
- FAISS or pgvector for large-scale vector storage
- E2E coverage gate at 95% in CI
- OAuth2 providers (Google, GitHub)

---

## Migration Guide

### v1.0 → v1.1

1. Apply database migration `002_add_vector_tables.sql`
2. Configure `REDIS_URL` for production (recommended)
3. Set `STORAGE_ROOT` environment variable
4. Run vector worker: `npm run vector:worker`

### v1.1 → v1.1.1

1. Run `python run_migrations.py` — the new `schema_migrations` tracking table ensures idempotent re-application
2. No breaking changes. All existing endpoints remain stable.

### Breaking Changes

None in v1.1 upgrade. All new features are additive.

---

## Deprecations

None currently. All existing endpoints remain stable.

---

For support, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) or open an issue on [GitHub](https://github.com/Sky-254-1/Nebula-search-engine-/issues).
