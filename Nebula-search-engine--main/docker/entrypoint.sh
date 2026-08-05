#!/bin/bash
set -euo pipefail

echo "Starting Nebula Search Engine..."

# ── Wait for PostgreSQL (skip when using SQLite) ────────────────────────────
if echo "${DATABASE_URL:-}" | grep -q "postgresql"; then
    echo "Waiting for PostgreSQL..."
    for i in $(seq 1 30); do
        if python -c "
import asyncio, asyncpg, os
async def chk():
    await asyncpg.connect(os.environ['DATABASE_URL'])
asyncio.run(chk())
" 2>/dev/null; then
            echo "PostgreSQL is ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "PostgreSQL connection failed after 30 attempts"
            exit 1
        fi
        echo "  attempt $i/30…"
        sleep 1
    done

    # ── Run database migrations on PostgreSQL ────────────────────────────────
    echo "Running database migrations..."
    cd /app
    python -m app.database.migrate upgrade head
    echo "Migrations completed"
else
    echo "Using SQLite — skipping PostgreSQL wait and migrations"
fi

# ── Wait for Redis (only if REDIS_URL is set) ───────────────────────────────
if [ -n "${REDIS_URL:-}" ]; then
    echo "Waiting for Redis..."
    for i in $(seq 1 30); do
        if python -c "
import redis, os
redis.from_url(os.environ['REDIS_URL']).ping()
" 2>/dev/null; then
            echo "Redis is ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "Redis not available after 30 attempts — continuing without cache"
            break
        fi
        echo "  attempt $i/30…"
        sleep 1
    done
else
    echo "REDIS_URL not set — running without distributed cache"
fi

mkdir -p /app/storage/uploads /app/storage/cache /app/storage/vector \
         /app/storage/indexes /app/storage/exports /app/logs

if [ $# -gt 0 ]; then
    echo "Starting application with command: $*"
    exec env PYTHONPATH=/app "$@"
else
    echo "Starting Uvicorn server..."
    cd /app
    exec env PYTHONPATH=/app uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level "${LOG_LEVEL:-info}"
fi
