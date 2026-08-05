#!/bin/sh
export PYTHONPATH=/app
while true; do
    python -c "from app.database.engine import connect; print('scheduler: heartbeat $(date)')" || true
    sleep 60
done
