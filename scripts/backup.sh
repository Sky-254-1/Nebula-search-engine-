#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$ROOT/docker/docker-compose.yml"
PROD="$ROOT/docker-compose.prod.yml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/database/backups/nebula_$TIMESTAMP.sql"
mkdir -p "$ROOT/database/backups"

echo "[Docker] Creating PostgreSQL backup..."
docker compose -f "$COMPOSE" -f "$PROD" exec -T postgres pg_dump -U nebula nebula > "$OUT"
echo "[Docker] Backup saved to $OUT"
