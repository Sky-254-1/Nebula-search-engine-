# Nebula Search Engine — Remediation Status Analysis

**Date:** 2026-07-21  
**Branch:** main  
**HEAD:** `99b886e` (documentation and update of features)  
**Original task set:** 8 remediation items + 4 acceptance criteria  

---

## 1. Executive Summary

Most of the original 8 remediation items have already been merged into `main` in commits between `5ef8d84` and `99b886e`. The remaining work is concentrated in **test infrastructure** (`backend/tests/conftest.py`), **git hygiene** (two tracked runtime files that need to be untracked), **CI alignment** (coverage threshold mismatch between local pytest.ini and GitHub Actions), and **verification** (fresh-venv boot + full test run).

There are also **11 unrelated uncommitted modifications** in the working tree that should be reviewed and either committed or discarded before proceeding.

---

## 2. Completed Items (already in HEAD)

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1a | `versioning.py`: add `Response` import | ✅ Done | Line 7: `from fastapi import HTTPException, Request, Response` |
| 1b | `response.py`: move `Response` to top-level import | ✅ Done | Line 9: `from fastapi.responses import JSONResponse, Response`; no dead bottom import |
| 1c | `monitoring.py`: move `Request` to top-level import | ✅ Done | Line 10: `from fastapi import Request` |
| 1d | `events.py`: move `import time` to top | ✅ Done | Line 6: `import time` |
| 1e | `main.py`: remove dead `slowapi` imports | ✅ Done | No `RateLimitExceeded` / `SlowAPIMiddleware` imports |
| 2 | Add missing deps (`numpy`, `tenacity`, `aiofiles`) | ✅ Done | `requirements.txt` lines 19-21 |
| 3 | Add `mypy` to `requirements-dev.txt` | ✅ Done | `requirements-dev.txt` line 5: `mypy>=1.8.0,<2.0.0` |
| 4a | Reconcile test suite (`testpaths`) | ✅ Done | `pytest.ini` line 3: `testpaths = ../tests tests` |
| 5 | Coverage gate to ~35% | ✅ Done | `pytest.ini` line 14: `fail_under = 35` |
| 6a | `.gitignore`: add `graphify-out/` | ✅ Done | `.gitignore` line 133 |
| 6b | `.gitignore`: add `storage/exports/**/*.json` | ✅ Done | `.gitignore` line 136 |
| 6c | `.gitignore`: add `test_results.txt`, `pytest_errors.txt` | ✅ Done | `.gitignore` lines 60-61 |
| 7 | JTI blacklist in `auth.py` | ✅ Done | Lines 166-174: checks `blacklisted_jti:{jti}` via `cache_service` |

---

## 3. Outstanding Items

### 3.1 Missing test infrastructure — `backend/tests/conftest.py` (CRITICAL)

**What:** `backend/tests/` contains 9 test modules (~277 tests) but has **no `conftest.py`**. The root `tests/conftest.py` exists and configures `DATABASE_URL`, `JWT_SECRET`, `APP_ENV`, `sys.path`, and shared fixtures (`client`, `auth_headers`, `setup_db`). Without an equivalent in `backend/tests/`, those tests may fail to import `app` or may run against a shared state.

**Risk:** `pytest` from `backend/` with `testpaths = ../tests tests` will collect backend tests, but module import paths and environment variables may leak or collide with root tests.

**Fix needed:** Create `backend/tests/conftest.py` that mirrors the root `tests/conftest.py` setup (env vars, sys.path, fixtures).

---

### 3.2 Runtime data files still tracked in git (MEDIUM)

**What:** `pytest_errors.txt` and `test_results.txt` are listed in `.gitignore` but are **still tracked** in the index.

```
$ git ls-files pytest_errors.txt test_results.txt
pytest_errors.txt
test_results.txt
```

`graphify-out/` and `storage/exports/` are already clean (not tracked in HEAD).

**Fix needed:**
```bash
git rm --cached pytest_errors.txt test_results.txt
git commit -m "chore: untrack runtime artifacts already covered by .gitignore"
```

---

### 3.3 CI vs local pytest.ini coverage mismatch (MEDIUM)

**What:**
- Local `backend/pytest.ini`: `fail_under = 35`
- `.github/workflows/ci.yml` line 40: `--cov-fail-under=75`

This means CI still enforces the old aspirational 75% threshold, while local runs allow 35%. If the intent is to baseline at ~35%, CI must be aligned.

**Fix needed:** Update `.github/workflows/ci.yml` line 40 to `--cov-fail-under=35` (or remove the flag and let pytest.ini govern).

---

### 3.4 CI test scope does not include `backend/tests/` (MEDIUM)

**What:** The CI workflow runs:
```yaml
pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=75
pytest tests/test_new_api_domains.py -v --cov=app --cov-append
```

This only executes the root `tests/` directory. The reconciled `pytest.ini` points `testpaths` at both `../tests` and `tests`, but CI overrides this with explicit commands and **never runs `backend/tests/`**.

**Fix needed:** Update CI workflow to run from `backend/` and let `pytest.ini` drive discovery, e.g.:
```yaml
pytest --cov=app --cov-report=term-missing --cov-report=xml
```
or explicitly add `backend/tests/` to the CI pytest invocation.

---

### 3.5 Uncommitted working-tree changes (LOW, but blocks clean status)

**What:** 11 files are modified but uncommitted:
- `Makefile`
- `backend/app/search/query_understanding/entity_extractor.py`
- `backend/app/search/query_understanding/intent_classifier.py`
- `backend/app/search/query_understanding/language_detector.py`
- `backend/app/search/query_understanding/query_processor.py`
- `backend/app/search/query_understanding/stemmer.py`
- `backend/app/search/query_understanding/stopwords.py`
- `backend/app/search/query_understanding/synonym_expander.py`
- `backend/app/search/query_understanding/tokenizer.py`
- `backend/pytest.ini`
- `tests/conftest.py`

These changes are unrelated to the original 8 remediation tasks and should be reviewed. If intentional, they should be committed; if stale, they should be discarded.

---

### 3.6 Verification from clean environment (PENDING)

The acceptance criteria require:
1. Fresh venv + `pip install -r backend/requirements.txt` + `python -c "from app.main import app"` succeeds
2. Full test suite (both `tests/` and `backend/tests/`) passes
3. `git status` clean of runtime-data files
4. `make typecheck` passes

These have **not been verified** against the current HEAD in a clean environment.

---

## 4. Gaps vs Original Acceptance Criteria

| Criterion | Current State | Gap |
|-----------|--------------|-----|
| Fresh venv import succeeds | Likely OK (imports fixed in HEAD) | Needs fresh-venv verification |
| Full test suite passes | Partially blocked: `backend/tests/` lacks `conftest.py`; CI doesn't run it | Need `conftest.py` + CI update |
| `git status` clean of runtime data | `pytest_errors.txt` & `test_results.txt` still tracked | Need `git rm --cached` |
| `make typecheck` passes | `mypy` added to requirements-dev | Needs actual `make typecheck` run in clean env |

---

## 5. Recommended Execution Order

1. **Create `backend/tests/conftest.py`** — unblock backend test execution
2. **Untrack runtime files** — `git rm --cached pytest_errors.txt test_results.txt`
3. **Align CI coverage threshold** — update `.github/workflows/ci.yml` to `--cov-fail-under=35`
4. **Align CI test scope** — ensure CI runs both `tests/` and `backend/tests/`
5. **Review/commit or discard working-tree changes** — clean the tree
6. **Run full verification** in a fresh venv:
   - `python -c "from app.main import app"`
   - `make typecheck`
   - `pytest` from `backend/` (covers both dirs via `testpaths`)
7. **Branch protection** — verify "Verify app imports" is a required check in GitHub repo settings (requires `gh` CLI or web UI)

---

## 6. Risk / Open Questions

- **`backend/tests/` tests may have been written assuming root `conftest.py` fixtures.** If they import `client` or `auth_headers` from the root conftest, duplicating the conftest in `backend/tests/` could cause double-registration of fixtures or database setup conflicts. Review imports in `backend/tests/test_*.py` before copying conftest blindly.
- **CI `--cov-fail-under=75` is hardcoded** in the workflow step, not inherited from `pytest.ini`. Even after lowering `pytest.ini` to 35%, CI will still fail at 75% until the workflow is updated.
- **Branch protection** cannot be verified or changed from within the repo without `gh` CLI. This is a manual GitHub settings step.
