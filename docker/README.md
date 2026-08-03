# Nebula Search Engine Docker Images

This directory contains Docker configurations for the Nebula Search Engine.

## Available Images

### Backend (Dockerfile.prod)
Production-ready Python backend with:
- Multi-stage build for minimal image size
- Non-root user (`nebula`) for security
- Health check endpoint at `/health/live`
- Readiness probe at `/health/ready`
- Detailed health check at `/health/detailed`

### Frontend (frontend.Dockerfile)
Production nginx server for serving the React frontend:
- Multi-stage build (Node.js for build, nginx for runtime)
- Non-root user (`nginx`) for security
- Static file caching with nginx configuration
- Rate limiting and security headers via nginx.prod.conf

### Vector Worker (vector.Dockerfile)
Background worker for vector indexing:
- Multi-stage build with FAISS dependencies
- Non-root user (`nebula`) for security
- Optional metrics endpoint at port 8001

## Usage

### Building Images

```bash
# Backend
docker build -f Dockerfile.prod -t nebula-backend .

# Frontend
docker build -f frontend.Dockerfile -t nebula-frontend .

# Vector Worker
docker build -f vector.Dockerfile -t nebula-vector .
```

### Running Containers

```bash
# Start all services with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## Security Features

- All containers run as non-root users
- Minimal base images (slim variants)
- Multi-stage builds to reduce attack surface
- Health checks for container orchestration
- Proper signal handling with dumb-init

## Image Size

- Backend: ~200MB (optimized with slim base and multi-stage build)
- Frontend: ~40MB (nginx alpine)
- Vector Worker: ~350MB (includes FAISS and numpy)
