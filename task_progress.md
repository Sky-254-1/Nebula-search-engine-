# Task Progress - Round 2 Fixes

## Analysis Complete - Ready to Implement

### Issue 1a: auth_extended.py - `validate_password` not imported
- Function exists in `app/services/auth.py` (line 18)
- Fix: Add `validate_password` to the import from `app.services.auth` on line 15

### Issue 1b: hybrid/routes.py - `current_user` not defined
- Route `hybrid_search` (line 102) references `current_user.id` but has no dependency injection for it
- Fix: Add `user_payload = Depends(get_current_user_token_payload)` parameter to route signature

### Issue 1c: rate_limit.py - `JSONResponse` not imported
- `rate_limit_exceeded_handler` (line 184) uses `JSONResponse` but only `Response` is imported
- Checked: It's imported in main.py but never registered as handler — dead code after SlowAPI removal
- Fix: Add `JSONResponse` to imports (safer than deleting dead code which might break transitive imports)

### Issue 2: test_vector.py test_hash_embedding
- Test calls `embed_text("test embedding")` without model param
- If sentence-transformers is installed, it returns semantic embedding, not "local-hash"
- Fix: Pass `model="local-hash"` to force the hash path

### Issue 3: RBAC tests (0% coverage)
- Write tests for `RBACService` covering:
  - `can_access_resource` for all roles (allow/deny paths)
  - `check_permission` for all roles
  - `get_user_permissions` for all roles
  - `get_role_level` and `has_role_hierarchy`
  - `get_inherited_roles`
  - `require_permission` / `require_any_permission` / `require_all_permissions`

### Issue 4: Untrack committed junk
- `git rm -r --cached storage/exports graphify-out`

### Issue 5: Mypy backlog (after fixing crash bugs)
- Run mypy after fixing NameErrors, then work through incrementally

### Issue 6: GitHub branch protection (manual)
- Confirm "CI" is required status check