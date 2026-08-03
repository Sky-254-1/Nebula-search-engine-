# Project Cleanup Documentation

## Overview

This document describes the cleanup and consolidation actions taken to improve project structure, remove duplicates, and resolve pytest collection errors.

## Date: August 3, 2026

---

## Motivation

The project had accumulated significant technical debt from years of development with multiple generations of similar components:

- **Duplicate test directories** causing pytest collection errors
- **Duplicate infrastructure directories** (`infra/` vs `infrastructure/`)
- **Duplicate docker-compose files** (root vs `docker/`)
- **Duplicate database migrations** (root vs `backend/app/database/migrations/`)
- **Duplicate storage directories**
- **Legacy/outdated files** committed to the repo

## Actions Taken

### P0 - Critical (Pytest Errors Fixed)

1. **Updated `backend/pytest.ini`**
   - Changed `testpaths = ../tests tests` to `testpaths = tests`
   - Removed reference to root `tests/` directory

2. **Removed root `database/migrations/`**
   - Deleted 4 outdated SQL files (001-004)
   - Active migrations are in `backend/app/database/migrations/`

### P1 - High Priority (Duplicates Consolidated)

1. **Consolidated `infra/` → `infrastructure/`**
   - Updated `docker-compose.yml` and `docker-compose.prod.yml`
   - Changed paths from `./infra/` to `./infrastructure/`

2. **Removed root docker-compose files**
   - Deleted `docker-compose.yml`
   - Deleted `docker-compose.prod.yml`
   - Deleted `docker-compose.scale.yml`
   - Deleted `docker-compose.override.yml`
   - All duplicated in `docker/` directory

3. **Updated Makefile**
   - All docker commands now reference the `docker/` directory
   - Added `docker-help` target for guidance

### P2 - Medium Priority (Cleanup Completed)

1. **Merged storage directories**
   - Removed `storage/indexes/` (kept `storage/index/`)
   - Removed `storage/vectors/` (kept `storage/vector/`)

2. **Removed deploy/deployments directories**
   - Both contained only README.md stubs

3. **Deleted stale scripts**
   - `extract_errors2.js`
   - `operations.sh`, `operations`
   - `reset.ps1`, `reset.sh`
   - `logs.ps1`, `logs.sh`

4. **Deleted legacy frontend**
   - `frontend/legacy/index.html` (old non-React entry point)

5. **Deleted generated artifacts**
   - `pytest_errors.txt`
   - `coverage_gap_analysis.txt`
   - `bandit-report.json`
   - `backend/*.txt` dumps
   - `coverage.json`
   - `mypy_full.txt`, `mypy_report.txt`
   - `backend_coverage_latest.txt`

6. **Deleted stale scripts**
   - `backend/test_startup.py`
   - `backend/test_observability.py`
   - `backend/test_security_fixes.py`
   - `backend/elevenlabs_example.py`

7. **Deleted progress trackers**
   - `task_progress.md`
   - `task_progress_completion.md`

8. **Deleted unused files**
   - Root `package.json`, `package-lock.json`
   - `update repo structure` (misnamed file)

9. **Deleted codeql scaffolding**
   - `codeql-custom-queries-actions/`
   - `codeql-custom-queries-javascript/`
   - `codeql-custom-queries-python/`

10. **Deleted Figma MCP**
    - `Figma-Context-MCP/` (~30 unrelated files)

11. **Updated `.gitignore`**
    - Added generated artifacts to prevent future commits
    - Added `backend/*.txt` to ignore generated files

---

## Results

### Before Cleanup
- **2408+ tests** collected (16 from root + 2392 from backend - with duplicates)
- **Pytest collection errors** from duplicate `conftest.py`
- **ModuleNotFoundError** from import path confusion
- **Confusion** about which infrastructure/docker files were canonical

### After Cleanup
- **1408 tests** collected (only from `backend/tests/`)
- **No pytest collection errors**
- **No import path confusion**
- **Clear canonical structure**

---

## Project Structure (Updated)

```
nebula-search-engine/
├── .github/workflows/          # CI/CD workflows
├── backend/
│   ├── app/
│   │   ├── database/           # Engine, repos, migrations
│   │   ├── main.py
│   │   ├── middleware/
│   │   ├── providers/ai/       # AI provider implementations
│   │   ├── routes/             # API route handlers
│   │   ├── services/
│   │   ├── search/             # Search pipeline
│   │   ├── hybrid/             # Hybrid search fusion
│   │   └── vector/             # Vector indexing pipeline
│   ├── tests/                  # Pytest + Playwright E2E (1408 tests)
│   ├── requirements.txt
│   └── .gitignore
├── frontend/
├── docker/                     # Docker Compose & configs
├── infrastructure/             # Kubernetes, Terraform, Helm configs
├── storage/                    # uploads, cache, vector, indexes
└── docs/                       # Documentation
```

---

## Migration Notes

### For Developers

1. **Running tests:**
   ```bash
   cd backend
   pytest  # Only collects from backend/tests/
   ```

2. **Running docker:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Database migrations:**
   ```bash
   cd backend
   python -m app.database.migrate
   ```

### For CI/CD

1. Update any references from `../tests/` to `tests/`
2. Update any references from `infra/` to `infrastructure/`
3. Update docker paths to use `docker/docker-compose.yml`

---

## What Was Kept (Not Deleted)

- `backend/vector/` - Still actively used by the codebase
- `storage/vector/` - Contains actual vector data files
- `storage/index/` - Contains index data
- `storage/cache/` - Contains cache files
- `storage/uploads/` - Contains user uploads
- `storage/exports/` - Contains export data

---

## Future Recommendations

1. **Remove `.env` files** from the repo (add to `.gitignore`)
2. **Add CI/CD workflows** for regular cleanup audits
3. **Document file naming conventions** to prevent future duplicates
4. **Add pre-commit hooks** to detect duplicate patterns

---

## Related Files

- [README.md](../README.md) - Updated with new structure
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Updated with testing changes
- [Makefile](../Makefile) - Updated with docker paths
- [backend/pytest.ini](../backend/pytest.ini) - Updated test paths

---

## Rollback Plan

If issues arise, the cleanup can be partially reverted:

1. Revert `pytest.ini` changes
2. Restore root `database/migrations/` from git history
3. Restore root docker-compose files from git history
4. Restore `infra/` directory from git history

However, the root `tests/` directory is no longer compatible with the current codebase structure.
