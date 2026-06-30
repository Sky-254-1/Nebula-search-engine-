# Nebula Search Engine — Dependencies Audit

## Python Dependencies (backend/requirements.txt)

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| fastapi | >=0.104.1 | ✅ | Recent |
| uvicorn | >=0.24.0 | ✅ | Recent |
| PyJWT | >=2.8.0 | ✅ | Recent |
| httpx | >=0.25.2 | ✅ | Recent |
| asyncpg | >=0.29.0 | ✅ | Recent |
| redis | >=5.0.0 | ✅ | Recent |
| pydantic | >=2.9.0 | ✅ | Recent |
| aiosqlite | >=0.19.0 | ✅ | Recent |
| python-multipart | >=0.0.6 | ✅ | Recent |

### Missing Critical Dependencies
| Package | Purpose | Priority |
|---------|---------|----------|
| alembic | Database migrations | HIGH |
| opentelemetry-api | Observability | HIGH |
| opentelemetry-sdk | Observability | HIGH |
| prometheus-client | Metrics | HIGH |
| bcrypt/argon2 | Password hashing | HIGH |
| python-jose[cryptography] | JWT with better algorithms | MEDIUM |
| slowapi | Rate limiting | MEDIUM |
| sentry-sdk | Error tracking | MEDIUM |
| gunicorn | Production WSGI | MEDIUM |
| aioredis | Redis async (already using redis.asyncio) | LOW |

## Frontend Dependencies (frontend/package.json)

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| react | ^18.3.1 | ✅ | Recent |
| react-dom | ^18.3.1 | ✅ | Recent |
| react-router-dom | ^6.28.0 | ✅ | Recent |
| vite | ^8.1.0 | ✅ | Very recent |

### Missing Frontend Dependencies
| Package | Purpose | Priority |
|---------|---------|----------|
| @tanstack/react-query | Data fetching/caching | HIGH |
| zustand | State management | HIGH |
| react-hook-form | Form handling | MEDIUM |
| zod | Schema validation | MEDIUM |
| tailwindcss | Styling | MEDIUM |
| vitest | Testing | HIGH |
| @testing-library/react | Testing | HIGH |
| i18next | Internationalization | MEDIUM |
| workbox-webpack-plugin | PWA | MEDIUM |
