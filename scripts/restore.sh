#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$ROOT/docker/docker-compose.yml"
PROD="$ROOT/docker-compose.prod.yml"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup-file.sql>"
    exit 1
fi

INPUT="$1"
if [ ! -f "$INPUT" ]; then
    echo "Backup file not found: $INPUT"
    exit 1
fi

echo "[Docker] Restoring PostgreSQL from $INPUT..."
docker compose -f "$COMPOSE" -f "$PROD" exec -T postgres psql -U nebula nebula < "$INPUT"
echo "[Docker] Restore completed successfully."
