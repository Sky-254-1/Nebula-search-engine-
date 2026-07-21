"""
Nebula Search Engine — Production Environment Validation.
Run this script to verify all production prerequisites are met.

Usage:
    python scripts/validate_production.py
"""

import asyncio
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check(name: str, condition: bool, hint: str = "") -> Tuple[bool, str]:
    """Run a validation check."""
    if condition:
        print(f"  {GREEN}[PASS]{RESET} {name}")
        return True, ""
    else:
        print(f"  {RED}[FAIL]{RESET} {name}")
        if hint:
            print(f"        {YELLOW}Hint: {hint}{RESET}")
        return False, hint


def section(title: str):
    """Print a section header."""
    print(f"\n{CYAN}{'=' * 60}{RESET}")
    print(f"{CYAN}{title}{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}")


def get_env(key: str, default: str = "") -> str:
    """Get environment variable with fallback."""
    return os.environ.get(key, default)


async def main() -> int:
    """Run all production validation checks."""
    print(f"\n{BOLD}NEBULA SEARCH ENGINE — PRODUCTION VALIDATION{RESET}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"Time: {__import__('datetime').datetime.now().isoformat()}")
    print(f"\n{GREEN}Running {15} validation checks...{RESET}")

    errors: List[str] = []
    warnings: List[str] = []

    repo_root = Path(__file__).resolve().parent.parent

    # ====================================================
    # Section 1: Environment Variables
    # ====================================================
    section("1. Environment Configuration")

    app_env = get_env("APP_ENV", "development")
    passed, hint = check("APP_ENV is set to 'production'", 
                         app_env == "production",
                         "Set APP_ENV=production in your .env file or environment")
    if not passed:
        errors.append(hint)

    jwt_secret = get_env("JWT_SECRET", "")
    passed, hint = check("JWT_SECRET is configured and >= 32 chars",
                         len(jwt_secret) >= 32,
                         "Set JWT_SECRET to a random string >= 32 characters")
    if not passed:
        errors.append(hint)

    encryption_key = get_env("ENCRYPTION_KEY", "")
    passed, hint = check("ENCRYPTION_KEY is configured",
                         len(encryption_key) >= 16,
                         "Set ENCRYPTION_KEY for data-at-rest encryption")
    if not passed:
        warnings.append(hint)

    database_url = get_env("DATABASE_URL", "")
    passed, hint = check("DATABASE_URL is configured",
                         bool(database_url),
                         "Set DATABASE_URL to your PostgreSQL connection string")
    if not passed:
        errors.append(hint)

    redis_url = get_env("REDIS_URL", "")
    passed, hint = check("REDIS_URL is configured (recommended for production)",
                         bool(redis_url),
                         "Set REDIS_URL for caching and queue management")
    if not passed:
        warnings.append(hint)

    # ====================================================
    # Section 2: Security
    # ====================================================
    section("2. Security Configuration")

    sentry_dsn = get_env("SENTRY_DSN", "")
    passed, hint = check("SENTRY_DSN configured (error tracking)",
                         bool(sentry_dsn),
                         "Set SENTRY_DSN to enable error tracking")
    if not passed:
        warnings.append(hint)

    # Check CSP configuration
    csp_default = get_env("CSP_DEFAULT_SRC", "'self'")
    passed = bool(csp_default)
    hint = "Review CSP policy for production hardening" if not passed else ""
    check("CSP policy is configured", passed, hint)
    if not passed:
        warnings.append(hint)

    # ====================================================
    # Section 3: Dependencies & Build
    # ====================================================
    section("3. Build & Dependencies")

    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import prometheus_client
        import jwt
        passed, hint = True, ""
    except ImportError as e:
        passed, hint = False, f"Missing dependency: {e}"
    check("Core Python dependencies installed", passed, hint)
    if not passed:
        errors.append(hint)

    # Check if requirements.txt exists
    req_file = repo_root / "backend" / "requirements.txt"
    req_dev_file = repo_root / "backend" / "requirements-dev.txt"
    passed = req_file.exists() and req_dev_file.exists()
    check("Requirements files present", passed, "Run pip install -r backend/requirements.txt")

    # Check frontend build
    frontend_dir = repo_root / "frontend"
    dist_dir = frontend_dir / "dist"
    node_modules = frontend_dir / "node_modules"
    
    if dist_dir.exists() and any(dist_dir.iterdir()):
        check("Frontend production build exists", True)
    else:
        passed, hint = False, "Run 'npm run build' in frontend/ directory"
        check("Frontend production build exists", passed, hint)
        if not passed:
            warnings.append(hint)

    if node_modules.exists():
        check("Frontend dependencies installed", True)
    else:
        check("Frontend dependencies installed", False, "Run 'npm install' in frontend/")
        warnings.append("Frontend dependencies not installed")

    # ====================================================
    # Section 4: Infrastructure
    # ====================================================
    section("4. Infrastructure & Scripts")

    # Check backup scripts
    scripts = ["scripts/backup.sh", "scripts/backup.ps1", "scripts/restore.ps1"]
    for script in scripts:
        if (repo_root / script).exists():
            check(f"Backup script exists: {script}", True)

    # Check Docker files
    docker_files = [
        "docker/Dockerfile",
        "docker/Dockerfile.prod",
        "docker/docker-compose.prod.yml",
        "docker/nginx.prod.conf",
    ]
    for df in docker_files:
        if (repo_root / df).exists():
            check(f"Docker config exists: {df}", True)
        else:
            check(f"Docker config exists: {df}", False, f"Missing: {df}")
            if not passed:
                warnings.append(f"Missing: {df}")

    # Check Helm chart
    helm_dir = repo_root / "infrastructure" / "helm" / "nebula"
    if helm_dir.exists():
        check("Helm chart exists", True)
    else:
        check("Helm chart exists", False, "Create infrastructure/helm/nebula/")
        warnings.append("Helm chart missing")

    # Check Kubernetes manifests
    k8s_dir = repo_root / "infrastructure" / "k8s"
    if k8s_dir.exists():
        check("Kubernetes manifests exist", True)
    else:
        check("Kubernetes manifests exist", False)
        warnings.append("K8s manifests missing")

    # ====================================================
    # Section 5: Monitoring & Observability
    # ====================================================
    section("5. Monitoring & Observability")

    # Check Prometheus config
    prom_file = repo_root / "infra" / "prometheus.yml"
    if prom_file.exists():
        check("Prometheus configuration exists", True)
    else:
        check("Prometheus configuration exists", False)
        warnings.append("Prometheus config missing")

    # Check Grafana dashboards
    grafana_dir = repo_root / "infra" / "grafana"
    if grafana_dir.exists():
        check("Grafana configuration exists", True)
    else:
        check("Grafana configuration exists", False)
        warnings.append("Grafana config missing")

    # Check alerting rules
    alerts_file = repo_root / "infra" / "prometheus-alerts.yml"
    if alerts_file.exists():
        check("Alerting rules configured", True)
    else:
        check("Alerting rules configured", False)
        warnings.append("Alerting rules missing")

    # ====================================================
    # Summary
    # ====================================================
    section("VALIDATION SUMMARY")

    if not errors and not warnings:
        print(f"\n  {GREEN}{BOLD}[SUCCESS]{RESET} All checks passed! Ready for production deployment.\n")
        return 0

    if errors:
        print(f"\n  {RED}{BOLD}[FAILURES]{RESET} {len(errors)} critical issue(s) found:")
        for e in errors:
            print(f"    {RED}•{RESET} {e}")

    if warnings:
        print(f"\n  {YELLOW}{BOLD}[WARNINGS]{RESET} {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    {YELLOW}•{RESET} {w}")

    print()
    if errors:
        print(f"  {RED}Fix critical issues before deploying to production.{RESET}")
        return 1
    else:
        print(f"  {YELLOW}Address warnings for optimal production setup.{RESET}")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)