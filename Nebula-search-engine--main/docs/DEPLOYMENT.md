# Nebula Search — Deployment Guide

## Docker (Recommended)

1. Copy environment file:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Set production values in `backend/.env`:
   - `JWT_SECRET` — strong random secret
   - `APP_ENV=production`
   - `CORS_ORIGINS=https://your-domain.com`
3. Build and run:
   ```bash
   cd docker
   docker compose up --build -d
   ```

## Manual Production

1. Install Python 3.11 on the server.
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Set environment variables (see SETUP.md).
4. Run with a process manager:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
   ```
5. Serve `frontend/` via Nginx with TLS termination.

## Nginx Example

```nginx
server {
    listen 443 ssl;
    server_name search.yourdomain.com;

    ssl_certificate     /etc/ssl/certs/nebula.pem;
    ssl_certificate_key /etc/ssl/private/nebula.key;

    location / {
        root /var/www/nebula/frontend;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## v1.1 Vector indexing

When using Redis (`REDIS_URL`), run the vector worker to process document indexing jobs:

```bash
npm run vector:worker
# or Docker: docker compose up vector-worker
```

Without Redis, the API process drains in-memory index jobs automatically.

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs tests on push and pull requests.

## Checklist

- [ ] Set `JWT_SECRET` (never use default in production)
- [ ] Restrict `CORS_ORIGINS` to your frontend domain
- [ ] Enable HTTPS
- [ ] Configure API keys server-side only (never in frontend)
- [ ] Set up log aggregation and health check monitoring on `/health`
- [ ] Back up SQLite/PostgreSQL data volume
