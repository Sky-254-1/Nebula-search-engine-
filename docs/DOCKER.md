# Nebula Search — Docker Architecture and Operations

## 1. Services

| Service   | Image/Build               | Ports               | Role                            |
|-----------|---------------------------|---------------------|---------------------------------|
| postgres  | postgres:16-alpine        | 5432                | Primary relational database     |
| redis     | redis:7-alpine            | 6379                | Distributed cache & queues      |
| backend   | docker/Dockerfile         | 8000                | FastAPI REST server             |
| worker    | docker/Dockerfile         | internal            | Background indexing jobs        |
| scheduler | docker/Dockerfile         | internal            | Periodic background heartbeat   |
| frontend  | docker/frontend.Dockerfile| 3000                | Vite → Nginx static assets      |
| nginx     | nginx:1.25-alpine         | 80                  | Reverse proxy / static Hosting  |
| storage   | minio/minio               | 9000/9001           | S3-compatible object storage    |
| monitoring| prom/prometheus           | 9090                | Metrics scrape & alerting       |

## 2. Networking

* `nebula-internal` (bridge, internal: true) — postgres, redis, backend, worker, scheduler, storage
* `nebula-public` (bridge) — backend, frontend, nginx, storage, monitoring

Only `backend` and `nginx` expose ports externally. All services communicate on the `nebula-internal` network without IP exposure.

## 3. Startup Order

1. infrastructure: postgres, redis
2. data: storage (minio)
3. compute: backend (depends on postgres + redis)
4. background: worker, scheduler (depend on postgres + redis)
5. edge: frontend (depends on backend)
6. proxy: nginx (depends on frontend + backend)
7. monitoring: prometheus

Startup is orchestrated via `depends_on` + `healthcheck` conditions in Docker Compose.

## 4. Data Volumes

| Volume         | Service   | Backup Strategy               | Restore                        |
|----------------|-----------|-------------------------------|--------------------------------|
| postgres-data  | postgres  | Nightly `pg_dump | gzip`      | `gunzip | psql` from backup    |
| redis-data     | redis     | Optional RDB/AOF snapshot     | Replace volume with snapshot   |
| nebula-storage | backend   | Included in `database/backups`| Restore from backup archive    |
| minio-data     | storage   | Recurring minio mirror batch  | Replace volume or mc cp remote |
| prometheus-data| prometheus| Exported via remote storage    | Restore from snapshot          |

Backups are stored under `database/backups/`. Use scripts/backup.ps1.

## 5. Security

* **Non-root containers**: backend, frontend, nginx run as non-root users.
* **Image minimization**: multi-stage builds, `-slim` / `-alpine` base images.
* **Read-only mounts**: source code mounted read-only in production.
* **Secrets handling**: environment variables injected via `.env` (never committed). For production, use Docker Secrets or a vault.
* **Health checks**: every service exposes a healthcheck to enforce startup ordering.
* **Network isolation**: internal services are not reachable from outside the bridge.

## 6. Development Workflow

```powershell
# First time setup
copy backend\.env.example backend\.env
.\scripts\migrations.ps1
.\scripts\start.ps1           # development mode
.\scripts\logs.ps1             # tail logs
.\scripts\migrations.ps1       # apply new migrations
.\scripts\test.ps1             # run pytest suite
.\scripts\stop.ps1             # bring down containers
.\scripts\reset.ps1            # reset volumes and rebuild
```

## 7. Production Workflow

```powershell
# Configure backend\.env with production secrets
.\scripts\backup.ps1
.\scripts\start.ps1 prod       # production mode
.\scripts\migrations.ps1
.\scripts\logs.ps1
```

Production override (`docker-compose.prod.yml`) sets:
* 2 backend workers
* Multiple worker replicas
* Resource limits and monitoring
* Log rotation (`json-file`, max 10MB, max 3 files)
* Rollback via `failure_action: rollback`

## 8. Container Dependency Map

```
postgres <-- backend
postgres <-- worker
postgres <-- scheduler
redis     <-- backend
redis     <-- worker
backend   <-- frontend
backend   <-- nginx
frontend  <-- nginx
```

## 9. Deployment Checklist

* [ ] `backend/.env` configured with production secrets (JWT_SECRET, DATABASE_URL, etc.)
* [ ] `.env` not committed to version control
* [ ] Images tagged and pushed to container registry (docker hub or private)
* [ ] PostgreSQL backups scheduled and tested (restore procedure verified)
* [ ] Resource limits set in `docker-compose.prod.yml`
* [ ] Logging and monitoring configured (Prometheus + Grafana / ELK)
* [ ] Health checks pass on all services
* [ ] Nginx SSL configured (via separate ingress / cloud load balancer)
* [ ] CI/CD pipeline builds, tests, pushes, and deploys images
* [ ] Rollback procedure documented and tested

## 10. Common Failure Points

* **Port conflicts**: Ensure ports 80, 3000, 5432, 6379, 8000, 9000, 9090 are free on the host or remap in `.env`.
* **Insufficient shared memory**: Redis / PostgreSQL may need `--shm-size` if using custom containers.
* **Slow dependency installs**: Backend build runs `pip install` on every build. Use BuildKit cache mounts.
* **File permissions**: On some hosts, `nebula-storage` volume may be owned by root. Fix with `chown` or disable user namespace remap.
* **CORS misconfiguration**: Ensure `CORS_ORIGINS` matches the frontend URL; `nginx.conf` proxies `/api/` to backend.
* **PostgreSQL readiness**: Backend waits for healthy postgres. If migrations fail, check `DATABASE_URL` environment.
* **Redis SSL**: Redis prompt may require `rediss://` URLs in production; configure TLS if required by architecture.
* **Out of memory**: Reduce backend worker count or memory limits in production overrides.

## 11. CI/CD Integration

Build and test pipeline example:

```yaml
steps:
  - run: docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml build
  - run: docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
  - run: .\scripts\migrations.ps1
  - run: .\scripts\test.ps1
  - run: docker tag nebula-backend:dev registry.example.com/nebula-backend:$TAG
  - run: docker push registry.example.com/nebula-backend:$TAG
```

Container registry strategy:
* Tag images with git SHA + `latest`.
* Use digest pinning in production (`@sha256:...`) for reproducibility.
* Scan images with Trivy or Grype before push.
