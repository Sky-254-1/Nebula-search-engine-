# Changelog

## [1.1.0] - 2026-06-30

### Added

- Backend: OpenTelemetry instrumentation
- Backend: Prometheus metrics endpoint
- Backend: Sentry error tracking
- Backend: CSRF protection middleware
- Backend: CSP security headers
- Backend: bcrypt password hashing (backward-compatible)
- Backend: 2FA/TOTP support
- Backend: WebAuthn passkey support
- Backend: Crawler service with robots.txt parsing
- Backend: Search indexer with TF-IDF/BM25 ranking
- Backend: Alembic database migrations
- Backend: Full SQLAlchemy ORM models
- Backend: Rate limiting by user tier
- Backend: Structured JSON logging
- Backend: Graceful shutdown signal handlers
- Frontend: Dashboard, Profile, Settings, Analytics, Admin pages
- Frontend: Zustand state management
- Frontend: React Query data fetching
- Frontend: i18n support (English, Spanish)
- Frontend: Reusable UI component system
- Frontend: Responsive sidebar layout
- Frontend: Dark/light theme toggle
- Infrastructure: Kubernetes manifests
- Infrastructure: Prometheus + Grafana monitoring
- Infrastructure: OpenTelemetry collector
- Infrastructure: Loki log aggregation
- Infrastructure: Alertmanager configuration
- DevOps: Comprehensive GitHub Actions CI/CD
- Testing: Extended pytest suite (80+ tests)
- Testing: Crawler and indexer tests
- Documentation: Full API reference
- Documentation: Deployment guide
- Documentation: Contributing guide
- Documentation: Security policy

### Changed

- Refactored middleware for better composability
- Enhanced config with 50+ production settings
- Improved error handling with request IDs
- Enhanced health checks with dependency verification
- Rate limiting now supports tier-based and burst modes

### Fixed

- Password hashing upgraded to bcrypt with PBKDF2 fallback
- Secret validation on startup
- Database connection cleanup on shutdown

## [1.0.0] - 2026-05-15

### Added

- Initial release with FastAPI backend
- React frontend with Vite
- JWT authentication with refresh tokens
- Web search (Wikipedia, Brave, SerpAPI)
- AI answers with multi-provider routing
- Vector search with embeddings
- Document upload and indexing
- Docker Compose setup
- PWA support
