# Changelog

All notable changes to Nebula Search will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-07-01

### Added

- **Vector Search Pipeline** - Complete document indexing with text extraction
  - Supports PDF, DOCX, HTML, TXT, MD, JSON, CSV
  - Automatic text chunking (800 chars, 200 overlap)
  - Content hash deduplication
- **Citation Tracking** - Source attribution for search results
  - Track which chunks were cited in answers
  -APA/MLA/Chicago citation formatting helpers
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

### Changed

- **Search Orchestrator** - Improved result deduplication and ranking
- **AI Provider Router** - Better fallback logic for provider selection
- **Rate Limiting** - Path-specific rate limiting keys
- **Security Headers** - HSTS added for production environments

### Fixed

- **Security** - SQL injection in audit.py (placeholder substitution)
- **Session Management** - Session family revocation on logout
- **CORS Configuration** - Default localhost origins

### Security

- Added Content-Security-Policy headers
- Enhanced password policy enforcement
- Improved brute-force protection

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
- Email verification on signup
- Password reset flow
- OAuth2 providers (Google, GitHub)

---

## Migration Guide

### v1.0 → v1.1

1. Apply database migration `002_add_vector_tables.sql`
2. Configure `REDIS_URL` for production (recommended)
3. Set `STORAGE_ROOT` environment variable
4. Run vector worker: `npm run vector:worker`

### Breaking Changes

None in v1.1 upgrade. All new features are additive.

---

## Deprecations

None currently. All existing endpoints remain stable.

---

*For support, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)*
