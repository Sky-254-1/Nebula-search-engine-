#!/bin/bash
set -euo pipefail

# Nebula Search Engine - Database Backup Script
# Usage: ./backup.sh [postgres|redis|all]
# Default: all

BACKUP_TYPE="${1:-all}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
elif [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
backup_postgres() {
    echo "Backing up PostgreSQL..."
    BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
    
    docker exec nebula-postgres pg_dump -U ${POSTGRES_USER:-nebula} ${POSTGRES_DB:-nebula} | gzip > "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ]; then
        echo "✓ PostgreSQL backup created: $BACKUP_FILE"
        echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo "✗ PostgreSQL backup failed"
        return 1
    fi
}

# Redis backup
backup_redis() {
    echo "Backing up Redis..."
    BACKUP_FILE="$BACKUP_DIR/redis_${TIMESTAMP}.rdb.gz"
    
    docker exec nebula-redis redis-cli BGSAVE
    sleep 2
    docker cp nebula-redis:/data/dump.rdb - | gzip > "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ]; then
        echo "✓ Redis backup created: $BACKUP_FILE"
        echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo "✗ Redis backup failed"
        return 1
    fi
}

# MinIO backup
backup_minio() {
    echo "Backing up MinIO..."
    BACKUP_FILE="$BACKUP_DIR/minio_${TIMESTAMP}.tar.gz"
    
    # Create a temporary container to access MinIO data
    docker run --rm \
        --volumes-from nebula-storage \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf "/backup/minio_${TIMESTAMP}.tar.gz" -C /data .
    
    if [ -f "$BACKUP_FILE" ]; then
        echo "✓ MinIO backup created: $BACKUP_FILE"
        echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo "✗ MinIO backup failed"
        return 1
    fi
}

# Clean old backups
cleanup_old_backups() {
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "*.sql.gz" -o -name "*.rdb.gz" -o -name "*.tar.gz" | \
        while read -r file; do
            if [ $(($(date +%s) - $(date +%s -r "$file" 2>/dev/null || stat -c %Y "$file"))) -gt $((RETENTION_DAYS * 86400)) ]; then
                echo "  Removing: $file"
                rm -f "$file"
            fi
        done
}

# Create manifest
create_manifest() {
    MANIFEST_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.txt"
    cat > "$MANIFEST_FILE" << EOF
Nebula Search Engine Backup Manifest
=====================================
Timestamp: $(date)
Backup Type: $BACKUP_TYPE

Files:
EOF
    
    ls -lh "$BACKUP_DIR"/*${TIMESTAMP}* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' >> "$MANIFEST_FILE"
    
    echo "✓ Manifest created: $MANIFEST_FILE"
}

# Main execution
echo "==================================="
echo "Nebula Backup - $BACKUP_TYPE"
echo "==================================="

case $BACKUP_TYPE in
    postgres)
        backup_postgres
        ;;
    redis)
        backup_redis
        ;;
    minio)
        backup_minio
        ;;
    all)
        backup_postgres
        backup_redis
        backup_minio
        create_manifest
        ;;
    *)
        echo "Unknown backup type: $BACKUP_TYPE"
        echo "Usage: $0 [postgres|redis|minio|all]"
        exit 1
        ;;
esac

cleanup_old_backups

echo "==================================="
echo "Backup completed successfully"
echo "==================================="