# Nebula Search Engine - Deployment Guide

## Prerequisites

- Docker 24+ with Compose v2+
- 4+ GB RAM
- 2+ CPU cores
- PostgreSQL 16+ (or use bundled Postgres)
- Redis 7+ (or use bundled Redis)

## Quick Start (Development)

```bash
# Start development environment
docker-compose -f docker/docker-compose.dev.yml up --build

# Run migrations
python backend/run_migrations.py

# Run tests
cd backend && pytest tests/ -v
```

## Production Deployment

### Option 1: Docker Compose

```bash
# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Build and start
docker-compose -f docker/docker-compose.prod.yml build
docker-compose -f docker/docker-compose.prod.yml up -d

# Check status
docker-compose -f docker/docker-compose.prod.yml ps
docker-compose -f docker/docker-compose.prod.yml logs -f
```

### Option 2: Kubernetes

```bash
# Install Helm
# Apply Helm chart
helm upgrade --install nebula ./infrastructure/helm/nebula \
  -f infrastructure/helm/nebula/values-prod.yaml \
  -n nebula --create-namespace

# Verify deployment
kubectl -n nebula get pods
kubectl -n nebula get services
kubectl -n nebula get ingress
```

### Option 3: Direct Deployment

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost/db
export REDIS_URL=redis://localhost:6379/0
export JWT_SECRET=your-secret-key

# Run migrations
python backend/run_migrations.py

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Start workers
python -m vector.worker
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | No | Redis connection string (defaults to in-memory) |
| `JWT_SECRET` | Yes | Secret key for JWT tokens |
| `AI_PROVIDER` | No | AI provider: openai, ollama, auto (default: auto) |
| `OPENAI_API_KEY` | Conditional | OpenAI API key (if using OpenAI provider) |
| `OLLAMA_URL` | No | Ollama URL (if using local Ollama) |
| `STORAGE_ROOT` | No | Storage directory (default: ./storage) |
| `APP_ENV` | No | Environment: development, staging, production |

## Security

### SSL/TLS

Enable HTTPS in production:

```bash
# Configure in .env
NGINX_SSL=1
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/private/key.pem
```

### Secrets Management

Use environment variables or secret management tools:

```bash
# Docker Compose
docker-compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d

# Kubernetes
kubectl create secret generic nebula-secrets \
  --from-env-file=.env.secrets
```

## Monitoring

### Health Checks

| Endpoint | Description |
|----------|-------------|
| `/health/live` | Liveness check |
| `/health/ready` | Readiness check (all dependencies) |
| `/health/detailed` | Full system status |
| `/metrics` | Prometheus metrics |

### Logs

```bash
# Docker Compose
docker-compose -f docker/docker-compose.prod.yml logs -f

# Kubernetes
kubectl -n nebula logs -f deployment/nebula-backend
```

### Metrics

Prometheus metrics available at `/metrics`:

```
nebula_http_requests_total{method, path, status}
nebula_http_request_duration_seconds{method, path}
nebula_db_pool_size
nebula_cache_hits_total
nebula_cache_misses_total
```

## Maintenance

### Backups

```bash
# Run backup script
./scripts/backup.sh

# Or use Docker
docker-compose -f docker/docker-compose.prod.yml exec postgres pg_dump -U nebula nebula > backup.sql
```

### Logs Retention

- Audit logs: 365 days
- Search history: 90 days
- Cache: Configurable TTL

### Scaling

```bash
# Docker Compose
docker-compose -f docker/docker-compose.prod.yml up --scale backend=4

# Kubernetes
kubectl -n nebula scale deployment nebula-backend --replicas=4
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Verify PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Ensure network connectivity

2. **Redis unavailable**
   - Redis is optional (uses in-memory fallback)
   - Check REDIS_URL environment variable

3. **High memory usage**
   - Adjust container memory limits
   - Reduce worker count
   - Increase Redis maxmemory

4. **Health checks failing**
   - Check application logs
   - Verify database connectivity
   - Check for resource constraints

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug

# Run migrations with verbose output
python backend/run_migrations.py --verbose
```

## Support

For issues, check:
- `docs/DEPLOYMENT.md` - Detailed deployment guide
- `docs/QUALITY_SECURITY_BASELINE.md` - Quality and security standards
- GitHub Issues - Bug reports and feature requests
