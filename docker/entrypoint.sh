#!/bin/bash
set -euo pipefail

echo "Starting Nebula Search Engine Backend..."

# Wait for database to be ready
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

# Wait for Redis to be ready
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

# Create logs directory
mkdir -p /app/logs

# Note: Database migrations are handled by the application on startup

# Start Uvicorn directly
echo "Starting Uvicorn server..."
cd /app
exec env PYTHONPATH=/app uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
