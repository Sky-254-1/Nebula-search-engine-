#!/bin/bash
set -euo pipefail

echo "Starting Nebula Vector Worker..."

# Create storage directories
mkdir -p ${VECTOR_INDEX_PATH:-/app/storage/indexes}
mkdir -p ${STORAGE_CACHE:-/app/storage/cache}
mkdir -p /app/logs

# Wait for dependencies if configured
if [ -n "${WAIT_FOR_DB:-}" ]; then
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
fi

if [ -n "${WAIT_FOR_REDIS:-}" ]; then
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
fi

# Change to app directory
cd /app

# Check command argument
if [ "$1" = "worker" ]; then
    echo "Starting vector indexing worker..."
    exec env PYTHONPATH=/app python -c "
import asyncio
from app.indexing.worker import Worker

async def main():
    worker = Worker('vector-worker')
    await worker.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await worker.stop()

if __name__ == '__main__':
    asyncio.run(main())
"
elif [ "$1" = "metrics" ]; then
    echo "Starting metrics server on port 8001..."
    exec env PYTHONPATH=/app python -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            'status': 'healthy',
            'service': 'vector-worker',
            'timestamp': int(time.time())
        }
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        pass

server = HTTPServer(('0.0.0.0', 8001), MetricsHandler)
server.serve_forever()
"
else
    echo "Starting application with command: $*"
    exec env PYTHONPATH=/app "$@"
fi
