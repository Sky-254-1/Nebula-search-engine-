# Contributing to Nebula Search Engine

Welcome! We're thrilled you're interested in contributing to Nebula Search Engine. This guide will help you get started, whether you're fixing a bug, adding a feature, improving documentation, or anything in between.

## Code of Conduct

By participating, you agree to uphold a welcoming and respectful community:

- **Be respectful** — Treat everyone with dignity and professionalism.
- **Be constructive** — Focus on solutions, not blame.
- **Be collaborative** — Work together to find the best outcomes.
- **Be inclusive** — Welcome contributors of all backgrounds and experience levels.

Unacceptable behavior includes harassment, discriminatory language, personal attacks, or any conduct that creates an unsafe or unwelcoming environment. Report incidents to maintainers.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend development |
| Docker & Compose | Latest | Containerized full-stack setup |
| Git | Latest | Version control |
| PostgreSQL | 16 (prod) / optional (dev) | Production database |

## Setup Development Environment

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/Nebula-search-engine-.git
cd Nebula-search-engine-
```

If you plan to contribute back, fork the repo on GitHub first, then clone your fork and add the upstream remote:

```bash
git remote add upstream https://github.com/Sky-254-1/Nebula-search-engine-.git
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` — at minimum set `JWT_SECRET` to a random 32+ character string.

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. E2E testing setup (optional, for E2E changes)

```bash
cd ..
npm install
npm run e2e:install    # Installs Playwright Chromium
```

### 5. Run locally

```bash
# Terminal 1 — Backend (from backend/)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (from frontend/)
npm run dev
```

Open http://localhost:5173 for the React app, or http://localhost:8000/docs for interactive API docs.

## Development Workflow

### Branch from main

Always create feature branches from `main`. Never commit directly to `main`.

### Branch naming

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New features | `feature/vector-search` |
| `fix/` | Bug fixes | `fix/jwt-expiry` |
| `docs/` | Documentation | `docs/api-reference` |
| `refactor/` | Code refactoring | `refactor/ai-provider` |
| `test/` | Test additions | `test/e2e-auth` |
| `chore/` | Maintenance | `chore/deps-update` |

### Conventional commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`

**Examples:**

```
feat(search): add Brave Search backend support
fix(auth): handle expired refresh tokens gracefully
docs(api): add vector search endpoint documentation
test(ai): add streaming response test coverage
```

Keep commits atomic — one logical change per commit.

### Before pushing

1. Run backend tests: `cd backend && pytest`
2. Verify frontend builds: `cd frontend && npm run build`
3. Run linters if available
4. Update documentation if you added or changed functionality
5. Add any new environment variables to `.env.example`

## Code Style

### Python (Backend)

- **PEP 8** with a maximum line length of **100 characters**
- **Python 3.11+** typing: use `list[str]` not `List[str]`, `dict[str, int]` not `Dict[str, int]`
- **Imports order:** standard library → third-party → local (grouped with blank lines)
- **Type hints** required on all function signatures
- **Async first:** use `async def` for all route handlers and I/O-bound operations
- **Error handling:** raise `HTTPException` for API errors, use `logger.exception()` in except blocks
- **Repository pattern:** one file per repository class under `app/database/repositories/`
- **Route organization:** group by domain under `app/routes/`, use `APIRouter` with prefix and tags
- **Business logic:** keep in `app/services/`, not in route handlers
- **Configuration:** all config via `app/config.py` `Settings` dataclass, values from env vars
- **Logging:** use `logging.getLogger("nebula.*")` — never `print()` or `console.log()`
- **Secrets:** never hardcode — all secrets come from environment variables

### React (Frontend)

- **Prettier defaults** for formatting
- **Functional components** with hooks — no class components
- **API calls:** use the `client.js` facade, not raw `fetch`
- **State:** AuthContext for auth, SearchContext for search, Zustand for page-level state
- **Data fetching:** React Query for server state management
- **Routing:** React Router 6 with lazy-loaded route pages
- **Error boundaries:** use `ErrorBoundary` for component error handling
- **Styling:** CSS files under `src/styles/` — no inline styles
- **Logging:** no `console.log` in committed code

### General

- No breaking API changes — all new routes must be additive
- No feature removal from the legacy UI at `/legacy/`
- All new env vars must be added to `.env.example` and relevant docs
- Database changes must include Alembic migration or SQL migration files

## Testing Requirements

All contributions must maintain or improve test coverage. The target is **90% coverage** for backend code.

### Backend Tests (pytest)

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run tests matching a keyword
pytest -k "vector"

# Minimum coverage target: 90% (enforced in CI at 75%)
```

**What to test:**

| Component | Level | Examples |
|-----------|-------|----------|
| Auth service | Unit | Password hashing, JWT creation/validation |
| Search service | Integration | Provider dispatch, query sanitization |
| AI service | Unit | Provider routing, caching, failover |
| API routes | Integration | HTTP responses, error handling, auth guards |
| Middleware | Integration | Rate limiting, security headers, CSRF |
| Repositories | Integration | CRUD operations, migrations |
| Crawler | Unit | Robots.txt parsing, URL normalization |
| Indexer | Unit | TF-IDF/BM25 ranking, chunking |
| Vector pipeline | Integration | Document ingestion → chunk → embed → search |

### E2E Tests (Playwright)

```bash
# Ensure backend + frontend are running, then:
npm run e2e            # Headless run
npm run e2e:headed     # Visible browser for debugging
npm run e2e:ui         # Interactive Playwright UI mode

# View report
npm run e2e:report
```

**E2E test locations:**

- `tests/e2e/auth/` — Signup, login, logout, token refresh, 2FA
- `tests/e2e/search/` — Web search, orchestrated search
- `tests/e2e/ai/` — AI answers, streaming, synthesis
- `tests/e2e/offline/` — Offline search, PWA functionality
- `tests/e2e/mobile/` — Mobile-specific flows
- `tests/e2e/documents/` — Upload, vector search, indexing
- `tests/e2e/errors/` — Error states, rate limiting, auth failures

## Pull Request Process

### PR Description Template

```markdown
## Description
What does this PR do? Why is it needed?

## Changes
- List of specific changes
- With bullet points

## Testing
How did you test these changes?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Backward compatible (no breaking API changes)
- [ ] Runs on SQLite and PostgreSQL
- [ ] All new env vars added to .env.example
- [ ] Lint checks pass
```

### Review Checklist

1. **Self-review** — Review your diff carefully before requesting a review
2. **CI must pass** — All checks (pytest, frontend build, E2E) must be green
3. **At least one maintainer** must approve
4. **Review criteria:**
   - **Correctness:** Does the code do what it claims?
   - **Test coverage:** Are there adequate tests for the change?
   - **Security:** Are there any security concerns (XSS, CSRF, injection)?
   - **Performance:** Are there any performance bottlenecks?
   - **Style:** Does it follow project conventions?
5. **Address feedback** — Make requested changes or explain your reasoning
6. **Merge** — Squash merge preferred (keeps git history clean)

## Release Process

### Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0) — Breaking API or database changes
- **MINOR** (0.X.0) — New features, backward compatible
- **PATCH** (0.0.X) — Bug fixes, backward compatible

### Release Steps

1. **Create a release branch:** `release/vX.Y.Z`
2. **Update version** in `package.json` and backend version string
3. **Update CHANGELOG.md** following Keep a Changelog format
4. **Run full test suite:** `pytest --cov=app`, `npm run build`, `npm run e2e`
5. **Create a GitHub Release** with tag `vX.Y.Z`
6. **CI builds and pushes Docker images** automatically
7. **Deploy to staging** for verification
8. **Deploy to production** after sign-off

### Hotfix Process

For critical production bugs:

1. Branch from the release tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`
2. Fix, test, and update CHANGELOG
3. PR directly to `main` (bypass normal process with maintainer approval)
4. After merge, tag and release as a patch version

## How to Get Help

- **GitHub Issues** — Report bugs or request features at https://github.com/Sky-254-1/Nebula-search-engine-/issues
- **GitHub Discussions** — Ask questions or start a conversation at https://github.com/Sky-254-1/Nebula-search-engine-/discussions
- **Security issues** — Report confidentially to security@nebula.dev
- **Project documentation** — See `docs/` for architecture, setup, deployment, and API reference
