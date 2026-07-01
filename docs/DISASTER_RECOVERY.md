# Disaster Recovery Guide

This guide covers backup, restore, and recovery procedures for Nebula Search.

---

## Backup Strategy

### What to Back Up

| Component | Frequency | Retention | Storage Location |
|-----------|-----------|-----------|-----------------|
| PostgreSQL database | Hourly | 30 days | S3/Google Cloud Storage |
| User uploads | Daily | 90 days | S3/Google Cloud Storage |
| Redis cache | N/A | N/A | Not backed up (ephemeral) |
| Configuration | On change | Indefinite | Git repository |

### Backup Locations

```bash
# Database
BACKUP_DIR=/var/backups/nebula

# User uploads (document storage)
STORAGE_ROOT=/app/storage

# Configuration
CONFIG_DIR=/etc/nebula
```

---

## Database Backup

### PostgreSQL

```bash
# Full backup
pg_dump -h localhost -U nebula nebula > /var/backups/nebula/full-$(date +%Y%m%d-%H%M%S).sql

# Schema-only backup
pg_dump -h localhost -U nebula -s nebula > /var/backups/nebula/schema-$(date +%Y%m%d-%H%M%S).sql

# Data-only backup
pg_dump -h localhost -U nebula -a nebula > /var/backups/nebula/data-$(date +%Y%m%d-%H%M%S).sql

# Compression
pg_dump -h localhost -U nebula nebula | gzip > /var/backups/nebula/full-$(date +%Y%m%d-%H%M%S).sql.gz
```

### Automated Backup Script

```bash
# scripts/backup_database.sh
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/nebula"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Full backup with compression
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" | \
  gzip > "$BACKUP_DIR/full-$DATE.sql.gz"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

# Upload to cloud storage (if configured)
if [ -n "$CLOUD_STORAGE_BUCKET" ]; then
  aws s3 cp "$BACKUP_DIR/full-$DATE.sql.gz" "s3://$CLOUD_STORAGE_BUCKET/nebula/"
fi

echo "Backup completed: full-$DATE.sql.gz"
```

### Cron Job

```bash
# Add to crontab
0 * * * * /path/to/scripts/backup_database.sh >> /var/log/nebula_backup.log 2>&1
```

---

## User Uploads Backup

```bash
# scripts/backup_uploads.sh
#!/bin/bash
set -e

STORAGE_ROOT="/app/storage"
BACKUP_DIR="/var/backups/nebula/uploads"

DATE=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Compress user uploads
tar -czf "$BACKUP_DIR/uploads-$DATE.tar.gz" -C "$STORAGE_ROOT" uploads/

# Keep only last 90 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +90 -delete

echo "Uploads backup completed: uploads-$DATE.tar.gz"
```

---

## Database Restore

### From Full Backup

```bash
# Restore database
gunzip -c /var/backups/nebula/full-20260701-010000.sql.gz | \
  psql -h localhost -U nebula nebula

# Or if compressed backup
zcat /var/backups/nebula/full-20260701-010000.sql.gz | \
  psql -h localhost -U nebula nebula
```

### From Schema + Data

```bash
# Restore schema
psql -h localhost -U nebula nebula < /var/backups/nebula/schema-20260701-010000.sql

# Restore data
psql -h localhost -U nebula nebula < /var/backups/nebula/data-20260701-010000.sql
```

### Point-in-Time Recovery

```sql
-- Restore to specific timestamp
pg_restore --format=c --dbname=nebula --snapshot=20260701-010000 \
  /var/backups/nebula/20260701-010000.dump
```

---

## User Uploads Restore

```bash
# Extract uploads backup
tar -xzf /var/backups/nebula/uploads-20260701-010000.tar.gz -C /app/storage/

# Verify ownership
chown -R appuser:appuser /app/storage/uploads
```

---

## Recovery Procedures

### Complete System Recovery

1. **Stop all services**
   ```bash
   docker compose down
   ```

2. **Restore database**
   ```bash
   gunzip -c /var/backups/nebula/full-20260701-010000.sql.gz | \
     psql -h localhost -U nebula nebula
   ```

3. **Restore uploads**
   ```bash
   tar -xzf /var/backups/nebula/uploads-20260701-010000.tar.gz -C /app/storage/
   ```

4. **Rebuild application**
   ```bash
   docker compose build
   ```

5. **Start services**
   ```bash
   docker compose up -d
   ```

6. **Verify**
   ```bash
   docker compose exec backend python -c "from app.main import app; print(app.title)"
   curl http://localhost:8000/health
   ```

### Database Corruption Recovery

```sql
-- Check database integrity
VACUUM ANALYZE;

-- Check for corrupted indexes
REINDEX DATABASE nebula;

-- Check for corrupted tables
SELECT * FROM pg_catalog.pg_tables WHERE schemaname = 'public';

-- Verify foreign key constraints
SELECT * FROM information_schema.table_constraints 
WHERE constraint_type = 'FOREIGN KEY';
```

### Data Loss Recovery

```bash
# Identify deleted data time range
psql -h localhost -U nebula nebula -c \
  "SELECT * FROM audit_logs WHERE action = 'delete' ORDER BY created_at DESC LIMIT 10"

# Restore from backup before deletion time
pg_restore --format=c --dbname=nebula --section=data \
  --snapshot=20260701-000000 /var/backups/nebula/20260701-000000.dump
```

---

## Recovery Testing

### Monthly DR Test

1. **Create test environment**
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. **Restore from latest backup**
   ```bash
   scripts/restore_test.sh
   ```

3. **Verify data integrity**
   ```bash
   docker compose exec backend python scripts/verify_data.py
   ```

4. **Test application functionality**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/search/web?q=test
   ```

5. **Clean up**
   ```bash
   docker compose down
   ```

### Annual DR Drill

1. **Simulate complete data center failure**
2. **Execute recovery from off-site backup**
3. **Measure RTO (Recovery Time Objective)**
4. **Measure RPO (Recovery Point Objective)**
5. **Document lessons learned**

---

## Backup Verification

### Automated Verification

```python
# scripts/verify_backup.py
import subprocess
import sys

def verify_backup(backup_path):
    """Verify backup integrity."""
    try:
        # Test gzip integrity
        result = subprocess.run(
            ['gunzip', '-t', backup_path],
            capture_output=True,
            timeout=300
        )
        if result.returncode != 0:
            return False, "Backup file is corrupted"
        
        # Test SQL syntax
        result = subprocess.run(
            ['psql', '-d', 'postgres', '--file', backup_path],
            capture_output=True,
            timeout=300
        )
        if result.returncode != 0:
            return False, "SQL syntax error"
        
        return True, "Backup verified"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    backup_path = sys.argv[1]
    valid, message = verify_backup(backup_path)
    print(f"Verification: {message}")
    sys.exit(0 if valid else 1)
```

### Schedule Verification

```bash
# Add to crontab (weekly verification)
0 3 * * 0 /path/to/scripts/verify_backup.py /var/backups/nebula/full-$(date -d last-sunday +%Y%m%d).sql.gz >> /var/log/nebula_backup_verify.log 2>&1
```

---

## RTO/RPO Targets

| Scenario | RTO | RPO |
|----------|-----|-----|
| Database failure | 1 hour | 1 hour |
| Full system failure | 4 hours | 24 hours |
| Data corruption | 2 hours | Latest backup |
| User data loss | 1 hour | Latest backup |

---

## Contact

For disaster recovery assistance:
- **Email:** ops@nebula-search.example.com
- **PagerDuty:** nebula-ops (if configured)
- **Slack:** #incidents

---

*Last updated: July 1, 2026*
