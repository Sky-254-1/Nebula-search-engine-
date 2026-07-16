#!/bin/bash
set -euo pipefail

echo "Starting Nebula Search Engine..."

echo "Waiting for database..."
for i in {1..30}; do
    if python -c "import asyncpg; asyncpg.connect('${DATABASE_URL}')" 2>/dev/null; then
        echo "Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Database connection failed after 30 attempts"
        exit 1
    fi
    sleep 1
done

echo "Waiting for Redis..."
for i in {1..30}; do
    if python -c "import redis; redis.from_url('${REDIS_URL}').ping()" 2>/dev/null; then
        echo "Redis is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Redis connection failed after 30 attempts"
        exit 1
    fi
    sleep 1
done

mkdir -p /app/logs

if [ $# -gt 0 ]; then
    echo "Starting application with command: $*"
    exec env PYTHONPATH=/app "$@"
else
    echo "Starting Uvicorn server..."
    cd /app
    exec env PYTHONPATH=/app uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info
fi
