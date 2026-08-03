#!/bin/bash
set -euo pipefail

echo "Starting Nebula Search Engine..."

# Wait for database connection
echo "Waiting for database..."
MAX_DB_ATTEMPTS=${MAX_DB_ATTEMPTS:-30}
DB_URL=${DATABASE_URL:-nebula.db}

for i in $(seq 1 $MAX_DB_ATTEMPTS); do
    if [ "$DB_URL" != "nebula.db" ]; then
        # PostgreSQL connection
        if python -c "
import asyncio
import asyncpg

async def check():
    url = '${DB_URL}'.replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.execute('SELECT 1')
    await conn.close()
    
asyncio.run(check())
" 2>/dev/null; then
            echo "Database is ready"
            break
        fi
    else
        # SQLite - just check if the directory exists
        DB_DIR=$(dirname "$DB_URL")
        if [ -d "$DB_DIR" ] || [ "$DB_URL" = "nebula.db" ]; then
            echo "Database (SQLite) is ready"
            break
        fi
    fi
    
    if [ "$i" -eq "$MAX_DB_ATTEMPTS" ]; then
        echo "Database connection failed after $MAX_DB_ATTEMPTS attempts"
        exit 1
    fi
    echo "  Attempt $i/$MAX_DB_ATTEMPTS - database not ready, waiting..."
    sleep 1
done

# Wait for Redis connection (only if configured)
echo "Waiting for Redis..."
MAX_REDIS_ATTEMPTS=${MAX_REDIS_ATTEMPTS:-30}
if [ -n "${REDIS_URL:-}" ]; then
    for i in $(seq 1 $MAX_REDIS_ATTEMPTS); do
        if python -c "
import asyncio
import redis

async def check():
    r = redis.from_url('${REDIS_URL}')
    await r.ping()
    await r.close()
    
asyncio.run(check())
" 2>/dev/null; then
            echo "Redis is ready"
            break
        fi
        if [ "$i" -eq "$MAX_REDIS_ATTEMPTS" ]; then
            echo "Redis connection failed after $MAX_REDIS_ATTEMPTS attempts"
            exit 1
        fi
        echo "  Attempt $i/$MAX_REDIS_ATTEMPTS - Redis not ready, waiting..."
        sleep 1
    done
else
    echo "Redis not configured (using in-memory cache)"
fi

# Create required directories
echo "Creating required directories..."
mkdir -p /app/logs
mkdir -p /app/storage/uploads
mkdir -p /app/storage/cache
mkdir -p /app/storage/vector
mkdir -p /app/storage/indexes
mkdir -p /app/storage/exports

# Run database migrations if using PostgreSQL
if [ "$DB_URL" != "nebula.db" ]; then
    echo "Running database migrations..."
    cd /app
    if python -m app.database.migrate 2>/dev/null; then
        echo "Database migrations completed"
    else
        echo "Warning: Database migrations skipped or failed (non-fatal)"
    fi
fi

if [ $# -gt 0 ]; then
    echo "Starting application with command: $*"
    exec env PYTHONPATH=/app "$@"
else
    echo "Starting Uvicorn server..."
    cd /app
    exec env PYTHONPATH=/app uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        --timeout-keep-alive 120
fi
