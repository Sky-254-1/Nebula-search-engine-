# Nebula Search Engine — Technical Debt Report

## Code Quality Issues

### Dead Code
| File | Issue | Action |
|------|-------|--------|
| `frontend/legacy/` | Legacy monolithic UI still shipped | Consider removing or documenting |
| `backend/vector/worker.py` | May contain duplicate logic | Review |
| `tests/` | Some extended tests may overlap with main tests | Consolidate |

### Duplicated Logic
| Pattern | Location | Count |
|---------|----------|-------|
| `_user_id()` helper | routes/storage.py, routes/vector.py | 2x — extract to shared |
| `sanitize_query()` | services/search.py | Could be used in more places |
| `hash_token()` | services/auth.py | Good utility — should be shared |

### Anti-patterns
| Pattern | Location | Fix |
|---------|----------|-----|
| `_ = email` discard | routes/ai.py:47, :82 | Remove unused parameter |
| Bare except clauses | services/auth.py:57 | Use specific exceptions |
| Nested exception handling | routes/auth.py CORS middleware | Use middleware properly |
| Import inside functions | app/main.py background worker | Move to top-level |
| `exec`-like pattern | N/A | Clean |

### Architecture Drift
| Area | Expected | Actual |
|------|----------|--------|
| Service layer | Routes → Services → Repos | Routes → Repos (services mixed) |
| API versioning | `/api/v1/` | ✅ Consistent |
| Error handling | Consistent error model | Mixed — some `HTTPException`, some `JSONResponse` |
| Dependency injection | Constructor injection | FastAPI `Depends()` (acceptable) |

## Test Debt
| Area | Coverage | Target |
|------|----------|--------|
| Unit tests (Python) | ~70% | 90%+ |
| Integration tests | ~40% | 80%+ |
| E2E tests | ~30% | 70%+ |
| Frontend tests | 0% | 80%+ |
| Load tests | 0% | Critical paths |

## Documentation Debt
| Area | Status |
|------|--------|
| API docs | ✅ OpenAPI auto-generated |
| Architecture docs | ⚠️ Partial |
| Deployment docs | ⚠️ Partial |
| Contributing guide | ❌ Missing |
| Security policy | ❌ Missing |
| Changelog | ❌ Missing |
