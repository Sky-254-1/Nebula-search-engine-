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

# Run database migrations if needed
echo "Running database migrations..."
python -m app.database.migrations.run_migrations || echo "Migrations skipped or failed"

# Create logs directory
mkdir -p /app/logs

# Start Gunicorn with Uvicorn workers
echo "Starting Gunicorn server..."
exec gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 60 \
    --keep-alive 5 \
    --graceful-timeout 30 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance