# Contributing to Nebula Search Engine

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the Nebula Search Engine project.

## Code of Conduct

By participating in this project, you agree to abide by the following:

- **Be respectful** — Treat all contributors with respect and professionalism.
- **Be constructive** — Focus on solving problems, not assigning blame.
- **Be collaborative** — Work together to find the best solutions.
- **Be inclusive** — Welcome contributions from people of all backgrounds.

Unacceptable behavior includes harassment, discriminatory language, personal attacks, or any conduct that creates an unsafe environment.

## Getting Started for Contributors

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional, for full-stack testing)
- Git
- A GitHub account

### Initial Setup

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/Nebula-search-engine-.git
cd Nebula-search-engine-

# Add upstream remote
git remote add upstream https://github.com/Sky-254-1/Nebula-search-engine-.git

# Create a branch for your work
git checkout -b feature/your-feature-name

# Set up backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env

# Set up frontend
cd ../frontend
npm install

# Set up E2E testing (optional, for E2E changes)
cd ..
npm install
npm run e2e:install
```

## Development Workflow

### Branch Naming

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New features | `feature/vector-search` |
| `fix/` | Bug fixes | `fix/jwt-expiry` |
| `docs/` | Documentation | `docs/api-reference` |
| `refactor/` | Code refactoring | `refactor/ai-provider` |
| `test/` | Test additions | `test/e2e-auth` |
| `chore/` | Maintenance tasks | `chore/deps-update` |

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

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

Commits should be atomic — one logical change per commit.

### Pull Request Process

1. **Create a feature branch** from `main` (never commit directly to `main`)
2. **Make your changes** following the coding standards below
3. **Run tests** locally to verify nothing is broken
4. **Update documentation** if you add or change functionality
5. **Create a pull request** against the `main` branch
6. **Ensure CI passes** — all checks must be green before review
7. **Address review feedback** — make requested changes and push

### PR Title and Description

```
Title: <type>(<scope>): <brief description>

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
```

## Coding Standards

### Python (Backend)

- **Python version:** 3.11+ (use modern typing: `list[str]` not `List[str]`)
- **Formatting:** Follow PEP 8 (120 character line limit)
- **Imports:** Standard library → third-party → local (grouped with blank lines)
- **Type hints:** Required on all function signatures
- **Async:** Use `async def` for all route handlers and I/O operations
- **Error handling:** Use HTTPException for API errors, log with logger.exception()
- **Repositories:** One file per repository class, under `app/database/repositories/`
- **Routes:** Group by domain under `app/routes/`, use `APIRouter` with prefix and tags
- **Services:** Keep business logic in `app/services/`, not in route handlers
- **Configuration:** All config via `app/config.py` Settings dataclass, values from env vars
- **No print()** — use `logging.getLogger("nebula.*")`
- **No hardcoded secrets** — all secrets come from environment variables

### JavaScript (Frontend)

- **Formatting:** Follow standard React conventions
- **Components:** Functional components with hooks (no classes)
- **API calls:** Use the `client.js` facade, not direct fetch calls
- **State:** Use AuthContext for auth state, SearchContext for search state
- **Routing:** Use React Router 6 with lazy loading for route pages
- **Error handling:** Use ErrorBoundary for component errors
- **No inline styles** — use CSS files under `src/styles/`
- **No console.log** in committed code

### General

- No breaking API changes — all new routes are additive
- No feature removal from the legacy UI at `/legacy/`
- All new env vars must be added to `.env.example` and `docs/SETUP.md`
- Database changes must include SQL migration files

## Testing Requirements

All contributions must maintain or improve test coverage.

### Backend Tests (pytest)

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run tests matching a keyword
pytest -k "vector"

# Coverage threshold: 75% minimum (enforced in CI)
```

**What to test:**
| Component | Test Level | Examples |
|-----------|------------|----------|
| Auth service | Unit | Password hashing, JWT creation/validation |
| Search service | Integration | Provider calls, query sanitization |
| AI service | Unit | Provider routing, caching |
| API routes | Integration | HTTP responses, error handling |
| Middleware | Integration | Rate limiting, security headers |
| Repositories | Integration | CRUD operations |

### Frontend Tests

Frontend testing is currently manual. When adding significant frontend logic:
- Test the change in both Chrome and Firefox
- Verify PWA functionality (service worker, install prompt)
- Check offline behavior

### E2E Tests (Playwright)

```bash
# Ensure backend + frontend are running, then:
npm run e2e
npm run e2e:headed   # Run with visible browser for debugging
npm run e2e:ui       # Interactive UI mode
```

**E2E test locations:**
- `tests/e2e/auth/` — Signup, login, logout, token refresh
- `tests/e2e/search/` — Web search, orchestrated search
- `tests/e2e/ai/` — AI answers, streaming
- `tests/e2e/offline/` — Offline search, PWA
- `tests/e2e/mobile/` — Mobile-specific flows
- `tests/e2e/documents/` — Upload, vector search
- `tests/e2e/errors/` — Error states, rate limiting

## PR Review Process

1. **Self-review first** — Check your diff carefully before requesting review
2. **Automated checks** — CI must pass (pytest, build, E2E)
3. **Code review** — At least one maintainer must approve
4. **Review criteria:**
   - Correctness: Does the code do what it claims?
   - Test coverage: Are there adequate tests?
   - Security: Are there any security concerns?
   - Performance: Are there any performance issues?
   - Style: Does it follow project conventions?
5. **Address feedback** — Make changes or explain why not
6. **Merge** — Squash merge preferred (clean history)

## Release Process

### Versioning

This project uses [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking API changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Steps

1. **Create a release branch:** `release/vX.Y.Z`
2. **Update version:** In `package.json`, `backend/app/main.py` (FastAPI version)
3. **Update CHANGELOG.md** following Keep a Changelog format
4. **Run full test suite:** pytest + frontend build + E2E
5. **Create GitHub Release** with tag `vX.Y.Z`
6. **Build and push Docker images** (CI handles this)
7. **Deploy to staging** for verification
8. **Deploy to production** after sign-off

### Hotfix Process

For critical bugs in production:
1. Branch from the release tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`
2. Fix and test
3. PR directly to `main` (bypass normal process if needed)
4. After merge, tag and release as patch version

## Questions?

If you have questions about contributing, please open a [GitHub Discussion](https://github.com/Sky-254-1/Nebula-search-engine-/discussions) or reach out to the maintainers.
