# Technical Design: Production Infrastructure, Security Hardening, and System Integration

## Overview

This document outlines the comprehensive technical design for transforming the Nebula Search Engine from a functional prototype into a production-ready, enterprise-grade search platform. The design addresses infrastructure, security, system integration, performance optimization, and observability requirements.

### Design Principles

1. **Defense in Depth**: Multiple security layers across network, application, and data layers
2. **Zero Trust Architecture**: Assume breach and verify all requests
3. **Infrastructure as Code**: All infrastructure defined in Terraform and Helm charts
4. **Observability First**: Comprehensive logging, metrics, and tracing from day one
5. **Performance by Design**: Optimized from the start, not as an afterthought
6. **Compliance by Default**: Built-in GDPR, SOC2, and OWASP compliance

### Scope Alignment

This design addresses all 31 requirements across:
- **Infrastructure & Deployment** (Requirements 1-5)
- **Security Hardening** (Requirements 6-12)
- **Terms and Conditions** (Requirements 13-17)
- **System Integration** (Requirements 18-22)
- **Performance Optimization** (Requirements 23-27)
- **Monitoring & Observability** (Requirements 28-31)

## Architecture Overview

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        WebBrowser[Web Browser]
        MobileApp[Mobile Application]
        APIConsumer[API Consumer]
    end

    subgraph "Edge Layer"
        Ingress[Nginx Ingress Controller]
        CDN[CDN - CloudFront/Cloudflare]
        WAF[WAF - OWASP Rules]
    end

    subgraph "Gateway Layer"
        APIGateway[API Gateway - Auth, Rate Limit, Routing]
        ServiceMesh[Service Mesh - mTLS, Observability]
    end

    subgraph "Application Layer"
        Backend[FastAPI Backend]
        Frontend[React Frontend]
        VectorWorker[Vector Search Worker]
        IndexWorker[Indexing Worker]
    end

    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL - Primary)]
        Redis[(Redis - Cache/Sessions)]
        FAISS[FAISS Vector Index]
        MinIO[MinIO - Object Storage]
    end

    subgraph "Monitoring Layer"
        Prometheus[Prometheus]
        Grafana[Grafana Dashboards]
        AlertManager[AlertManager]
        Loki[Loki - Logging]
        Jaeger[Jaeger - Tracing]
    end

    WebBrowser --> Ingress
    MobileApp --> Ingress
    APIConsumer --> APIGateway
    APIGateway --> ServiceMesh
    Ingress --> ServiceMesh
    
    ServiceMesh --> Backend
    ServiceMesh --> Frontend
    ServiceMesh --> VectorWorker
    ServiceMesh --> IndexWorker
    
    Backend --> PostgreSQL
    Backend --> Redis
    VectorWorker --> FAISS
    IndexWorker --> PostgreSQL
    IndexWorker --> MinIO
    
    Backend --> Prometheus
    VectorWorker --> Prometheus
    IndexWorker --> Prometheus
    
    Backend --> Loki
    VectorWorker --> Loki
    IndexWorker --> Loki
    
    Backend --> Jaeger
    VectorWorker --> Jaeger
    IndexWorker --> Jaeger
    
    Prometheus --> AlertManager
    Prometheus --> Grafana
    Loki --> Grafana
    Jaeger --> Grafana
```

### Component Interactions

#### 1. Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant APIGateway
    participant Backend
    participant Redis
    participant PostgreSQL

    Client->>APIGateway: POST /api/v1/auth/login
    APIGateway->>Backend: Validate JWT/Token
    Backend->>Redis: Check session/cache
    Redis-->>Backend: Session data (if cached)
    
    alt Cache Miss
        Backend->>PostgreSQL: Query user credentials
        PostgreSQL-->>Backend: User data
        Backend->>Backend: Verify password (PBKDF2)
        Backend->>Redis: Create session
        Backend-->>APIGateway: Access + Refresh tokens
    else Cache Hit
        Backend-->>APIGateway: Return cached tokens
    end
    
    APIGateway-->>Client: HTTP 200 + Tokens
```

#### 2. Search Query Flow

```mermaid
sequenceDiagram
    participant Client
    participant Backend
    participant Redis
    participant PostgreSQL
    participant VectorWorker
    participant FAISS

    Client->>Backend: GET /api/v1/search?q=query
    Backend->>Redis: Check search cache
    Redis-->>Backend: Cached results (if hit)
    
    alt Cache Miss
        Backend->>Backend: Parse query, extract entities
        Backend->>PostgreSQL: Full-text search + filters
        Backend->>VectorWorker: Semantic search request
        VectorWorker->>FAISS: Vector similarity search
        FAISS-->>VectorWorker: Similar documents
        VectorWorker-->>Backend: Vector results
        Backend->>Backend: Rerank & fuse results
        Backend->>Redis: Cache results (5 min TTL)
        Backend-->>Client: HTTP 200 + Results
    end
```

#### 3. Document Upload Flow

```mermaid
sequenceDiagram
    participant Client
    participant Backend
    participant Redis
    participant MinIO
    participant IndexWorker
    participant PostgreSQL

    Client->>Backend: POST /api/v1/documents/upload
    Backend->>MinIO: Upload document (streaming)
    MinIO-->>Backend: Document ID
    Backend->>Redis: Publish document.uploaded event
    Backend-->>Client: HTTP 202 Accepted
    
    IndexWorker->>Redis: Subscribe to events
    IndexWorker->>PostgreSQL: Save metadata
    IndexWorker->>VectorWorker: Trigger indexing
    VectorWorker->>FAISS: Update vector index
    IndexWorker->>Redis: Publish document.indexed event
    IndexWorker->>PostgreSQL: Update status
```

### Data Flow Diagrams

#### Inbound Traffic Flow

```mermaid
graph LR
    A[Internet] --> B[Cloudflare/AWS CloudFront]
    B --> C[Acme WAF]
    C --> D[Nginx Ingress]
    D --> E[Service Mesh Proxy]
    E --> F[Backend Service]
    E --> G[Frontend Service]
    
    F --> H[Rate Limiter]
    H --> I[Auth Middleware]
    I --> J[Request Router]
    J --> K[Business Logic]
    K --> L[Database/Cache]
```

#### Outbound Traffic Flow

```mermaid
graph LR
    A[Backend Service] --> B[Vector Search API]
    B --> C[AI Provider OpenAI/Ollama]
    A --> D[External Search - Brave/SerpAPI]
    A --> E[Email Service - SMTP]
    A --> F[Webhook Service]
    
    C --> G[OpenAI API]
    D --> H[External APIs]
```

### Security Architecture

```mermaid
graph TB
    subgraph "Network Security"
        TLS[TLS 1.3 Encryption]
        WAF[Web Application Firewall]
        DDOS[DDoS Protection]
    end

    subgraph "Application Security"
        Auth[JWT + OAuth2 Authentication]
        RBAC[Role-Based Access Control]
        CSRF[CSRF Protection]
        InputValidation[Input Sanitization]
    end

    subgraph "Data Security"
        Encryption[AES-256 Data Encryption]
        KMS[Key Management Service]
        Masking[Data Masking in Logs]
    end

    subgraph "Operational Security"
        Secrets[Secrets Manager]
        Rotation[Automatic Secret Rotation]
        Auditing[Audit Logging]
        PenTesting[Regular Pen Testing]
    end

    TLS --> Auth
    WAF --> InputValidation
    Encryption --> KMS
    Secrets --> Rotation
    Auditing --> PenTesting
```

## Infrastructure Design

### Docker Multi-Stage Build Strategy

```dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11.9-slim-bookworm AS builder

WORKDIR /build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime - Minimal image
FROM python:3.11.9-slim-bookworm AS runtime

WORKDIR /app
RUN groupadd -r nebula && useradd -r -g nebula -m -d /home/nebula nebula

COPY --from=builder /install /home/nebula/.local
COPY --chown=nebula:nebula backend/app /app/app
COPY --chown=nebula:nebula backend/vector /app/vector

USER nebula
EXPOSE 8000
HEALTHCHECK --interval=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Resource Definitions

```yaml
# Backend Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nebula-backend
  labels:
    app: nebula-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nebula-backend
  template:
    metadata:
      labels:
        app: nebula-backend
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: backend
        image: nebula/backend:latest
        ports:
        - containerPort: 8000
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nebula-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Helm Chart Architecture

```yaml
# Chart.yaml
apiVersion: v2
name: nebula
description: Nebula Search Engine - Production Helm Chart
type: application
version: 2.0.0
appVersion: "2.0.0"

dependencies:
  - name: postgresql
    version: "~12.0"
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
  - name: redis
    version: "~18.0"
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled
```

```yaml
# values.yaml - Production Configuration
backend:
  replicaCount: 4
  image:
    repository: nebula/backend
    tag: "2.0.0"
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
  env:
    APP_ENV: production
    LOG_LEVEL: INFO
    LOG_JSON_FORMAT: "true"
    ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    JWT_SECRET: ${JWT_SECRET}
```

### Environment-Specific Configurations

```yaml
# values.development.yaml
backend:
  replicaCount: 1
  autoscaling:
    enabled: false
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 250m
      memory: 256Mi

# values.staging.yaml
backend:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 400m
      memory: 512Mi
```

## Security Design

### Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Redis
    participant PostgreSQL

    User->>Frontend: Enter credentials
    Frontend->>Backend: POST /api/v1/auth/login
    Backend->>Redis: Check account lockout
    Redis-->>Backend: Not locked
    
    Backend->>PostgreSQL: Query user by email
    PostgreSQL-->>Backend: User data + hashed password
    Backend->>Backend: Verify password (PBKDF2, 200k iterations)
    
    alt Valid
        Backend->>Redis: Create session + refresh token
        Backend-->>Frontend: Access token + refresh token
        Frontend->>Frontend: Store tokens in HTTP-only cookies
        Frontend->>User: Redirect to dashboard
    else Invalid
        Backend->>Backend: Increment failed attempts
        Backend-->>Frontend: HTTP 401 Unauthorized
        Frontend->>User: Show error message
    end
```

### API Security Architecture

#### Security Headers (enforced via middleware)

```python
# Security headers middleware
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
response.headers["Content-Security-Policy"] = settings.csp_policy
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
```

#### Rate Limiting Strategy

```python
# Rate limit tiers
RATE_LIMIT_TIER_BASIC = 30      # requests/minute
RATE_LIMIT_TIER_PRO = 120       # requests/minute
RATE_LIMIT_TIER_ENTERPRISE = 600 # requests/minute
```

### Database Security Strategy

#### Encryption at Rest

```python
# Encryption key management
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", secrets.token_bytes(32))

# AES-256 encryption for sensitive fields
def encrypt_data(data: str, key: bytes) -> str:
    # Implementation using cryptography library
    pass

def decrypt_data(token: str, key: bytes) -> str:
    # Implementation using cryptography library
    pass
```

#### Database Connection Security

```yaml
# PostgreSQL connection with TLS
DATABASE_URL: "postgresql://user:pass@host:5432/db?sslmode=require&sslrootcert=/certs/ca.pem&sslcert=/certs/client.pem&sslkey=/certs/client-key.pem"
```

### Secrets Management

```yaml
# Kubernetes Secrets
apiVersion: v1
kind: Secret
metadata:
  name: nebula-secrets
type: Opaque
stringData:
  jwt-secret: ${JWT_SECRET}  # 64+ characters
  database-password: ${DB_PASSWORD}
  redis-password: ${REDIS_PASSWORD}
  encryption-key: ${ENCRYPTION_KEY}
```

### OWASP Compliance Implementation

#### OWASP Top 10 Protections

| Vulnerability | Mitigation |
|---------------|-----------|
| A01:2021-Broken Access Control | RBAC, JWT validation, CSRF tokens |
| A02:2021-Cryptographic Failures | PBKDF2 hashing, AES-256 encryption, TLS 1.3 |
| A03:2021-Injection | Parameterized queries, input validation, escaping |
| A04:2021-Insecure Design | Threat modeling, secure patterns |
| A05:2021-Security Misconfiguration | Environment-specific configs, security headers |
| A06:2021-Vulnerable Components | Dependency scanning, SCA tools |
| A07:2021-Identification Failures | MFA, account lockout, session management |
| A08:2021-Software Data Integrity Failures | CI/CD signing, artifact verification |
| A09:2021-Security Logging Failures | Structured logging, SIEM integration |
| A10:2021-SSRF | URL validation, IP whitelist, network policies |

## Terms and Conditions Design

### Legal Terms Storage and Display

```python
# Terms data model
class TermsVersion(BaseModel):
    id: int
    version: str
    content: str  # HTML content
    effective_date: datetime
    requires_acceptance: bool = True
    created_at: datetime
    created_by: str

# API Endpoints
GET /api/v1/terms/latest          # Get latest terms
POST /api/v1/terms/accept         # Accept terms
GET /api/v1/terms/history         # Get terms history
```

### Privacy Policy Implementation

```python
# Privacy data model
class PrivacyPolicy(BaseModel):
    id: int
    version: str
    content: str  # HTML content
    last_updated: datetime
    gdpr_compliant: bool = True
    ccpa_compliant: bool = True
```

### Cookie Consent System

```mermaid
graph TB
    A[User visits site] --> B{Cookie banner shown?}
    B -->|No| C[Show banner with options]
    C --> D[User makes selection]
    D --> E[Store preferences in DB + cookies]
    E --> F[Enable/disable tracking]
    
    F --> G{Essential cookies?}
    G -->|Yes| H[Always enabled]
    G -->|No| I[Respect user choice]
    
    H --> J[Analytics]
    I --> J
    J --> K[Send to Analytics service]
```

### Data Retention Enforcement

```python
# Data retention policies
DATA_RETENTION = {
    "search_history": timedelta(days=90),
    "user_sessions": timedelta(days=30),
    "audit_logs": timedelta(days=365),
    "uploads": None,  # User-controlled
}

# Automated cleanup job
async def cleanup_expired_data():
    # Delete search history older than 90 days
    # Delete expired sessions
    # Update audit logs older than 1 year
    pass
```

## System Integration Design

### Microservices Communication Patterns

#### Event-Driven Architecture

```mermaid
graph TB
    subgraph "Event Producers"
        Backend[Backend Service]
        IndexWorker[Index Worker]
        VectorWorker[Vector Worker]
    end

    subgraph "Event Bus"
        RedisStreams[Redis Streams]
        RabbitMQ[RabbitMQ]
    end

    subgraph "Event Consumers"
        NotificationService[Notification Service]
        AnalyticsService[Analytics Service]
        EmailService[Email Service]
    end

    Backend --> RedisStreams
    IndexWorker --> RedisStreams
    VectorWorker --> RedisStreams
    
    RedisStreams --> NotificationService
    RedisStreams --> AnalyticsService
    RedisStreams --> EmailService
```

### API Gateway Configuration

```yaml
# Kong API Gateway configuration
_plugins:
  - name: jwt
    config:
      key_claim_name: kid
      claims_to_verify: [exp, iat]
  - name: rate-limiting
    config:
      minute: 60
      policy: cluster
  - name: request-transformer
    config:
      add:
        headers:
          - X-Request-ID: $proxy_host
```

### Service Mesh Configuration

```yaml
# Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: nebula-backend
spec:
  hosts:
  - nebula-backend
  http:
  - match:
    - headers:
        x-api-version:
          exact: v1
    route:
    - destination:
        host: nebula-backend
        port:
          number: 8000
        subset: v1
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Performance Design

### Database Optimization Strategy

#### Indexing Strategy

```sql
-- Search performance indexes
CREATE INDEX idx_documents_search_vector ON documents USING GIN(to_tsvector('english', content));
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_user_id ON documents(user_id);

-- Query optimization patterns
SELECT * FROM documents 
WHERE to_tsvector('english', content) @@ to_tsquery('query') 
  AND user_id = $1 
  AND created_at > NOW() - INTERVAL '30 days'
ORDER BY score DESC
LIMIT 20 OFFSET 0;
```

#### Connection Pool Configuration

```python
# Database pool settings
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

### Caching Architecture

```mermaid
graph TB
    Client --> CDN[CDN - Static Assets]
    Client --> Redis[Redis Cache]
    
    Backend --> Redis
    Frontend --> Redis
    
    Redis -->|5 min TTL| SearchResults[Search Results]
    Redis -->|1 hour TTL| DocumentMetadata[Document Metadata]
    Redis -->|30 min TTL| UserSessions[User Sessions]
    Redis -->|5 min TTL| SearchSuggestions[Search Suggestions]
```

### CDN and Frontend Optimization

```python
# Frontend bundle optimization
# - Code splitting by route
# - Lazy loading components
# - Image optimization (WebP, lazy loading)
# - Service worker for offline capability
# - Bundle size under 500KB gzipped
```

### Load Balancing Strategy

```yaml
# Nginx load balancing
upstream backend {
    least_conn;
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
    server backend-4:8000;
    
    keepalive 32;
}

server {
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring & Observability Design

### Logging Architecture

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "nebula-backend",
  "request_id": "abc123",
  "user_id": 123,
  "method": "GET",
  "path": "/api/v1/search",
  "status_code": 200,
  "duration_ms": 45,
  "message": "Search request completed",
  "metadata": {
    "query": "neural networks",
    "results_count": 15,
    "source": "web_search"
  }
}
```

### Distributed Tracing

```mermaid
graph TB
    A[Request Start] --> B[API Gateway]
    B --> C[Backend Service]
    C --> D[PostgreSQL]
    C --> E[Redis]
    C --> F[Vector Search]
    
    B -.->|"trace_id: abc123"| A
    C -.->|"trace_id: abc123, span: 001"| B
    D -.->|"trace_id: abc123, span: 002"| C
    E -.->|"trace_id: abc123, span: 003"| C
    F -.->|"trace_id: abc123, span: 004"| C
```

### Alerting Rules

```yaml
# Alerting rules
groups:
  - name: backend-alerts
    rules:
    - alert: HighErrorRate
      expr: sum(rate(nebula_http_requests_total{status=~"5.."}[5m])) / sum(rate(nebula_http_requests_total[5m])) * 100 > 1
      for: 5m
      labels:
        severity: critical
      
    - alert: HighLatency
      expr: histogram_quantile(0.95, sum(rate(nebula_http_request_duration_seconds_bucket[5m])) by (le)) > 0.5
      for: 10m
      labels:
        severity: warning
```

### Dashboard Design

```mermaid
graph TB
    Dashboard[Main Dashboard]
    
    Dashboard --> KPIs[KPIs: Uptime, Errors, Latency]
    Dashboard --> Traffic[Traffic Analysis]
    Dashboard --> Performance[Performance Metrics]
    Dashboard --> Database[Database Health]
    Dashboard --> Infrastructure[Infrastructure Status]
    
    KPIs --> UptimeChart[Uptime Chart]
    KPIs --> ErrorRateChart[Error Rate Chart]
    KPIs --> LatencyChart[Latency Distribution]
    
    Traffic --> RequestsChart[Requests Over Time]
    Traffic --> TopEndpoints[Top Endpoints]
    
    Performance --> CPUChart[CPU Usage]
    Performance --> MemoryChart[Memory Usage]
    Performance --> DBPoolChart[DB Pool Usage]
```

## Data Models and Database Schema

### Schema Updates

```sql
-- Terms and Conditions table
CREATE TABLE terms_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    requires_acceptance BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

-- Privacy policy table
CREATE TABLE privacy_policies (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,
    gdpr_compliant BOOLEAN DEFAULT TRUE,
    ccpa_compliant BOOLEAN DEFAULT TRUE
);

-- Cookie consent table
CREATE TABLE cookie_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN DEFAULT TRUE,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## API Design for New Endpoints

### Terms and Conditions API

```python
# GET /api/v1/terms/latest
@router.get("/terms/latest")
async def get_latest_terms():
    """Get the latest terms of service."""
    terms = await terms_service.get_latest()
    return {"data": terms}

# POST /api/v1/terms/accept
@router.post("/terms/accept")
async def accept_terms(
    request: Request,
    version: str = Body(..., embed=True)
):
    """Accept terms of service."""
    user_id = await get_user_id(request)
    await terms_service.accept(user_id, version)
    return {"message": "Terms accepted"}

# GET /api/v1/privacy/latest
@router.get("/privacy/latest")
async def get_privacy_policy():
    """Get the latest privacy policy."""
    policy = await privacy_service.get_latest()
    return {"data": policy}
```

## Security Implementation Details

### Audit Logging

```python
# Audit event structure
{
    "user_id": 123,
    "session_id": "abc123",
    "action": "login",
    "resource_type": "user",
    "resource_id": 123,
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "status": "success",
    "metadata": {
        "login_method": "password",
        "mfa_used": false
    }
}
```

### Secret Rotation

```python
# Automatic secret rotation
async def rotate_secret(secret_name: str):
    """Rotate a secret and update all services."""
    new_secret = secrets.token_urlsafe(64)
    
    # Update in secrets manager
    await secrets_manager.update(secret_name, new_secret)
    
    # Update in Kubernetes
    await k8s_client.update_secret(secret_name, new_secret)
    
    # Graceful rotation period
    await asyncio.sleep(300)  # Wait for services to reload
```

## Integration Points with Existing Systems

### Current Integration Map

```mermaid
graph TB
    subgraph "Existing Systems"
        FastAPI[FastAPI Backend]
        React[React Frontend]
        PostgreSQL[PostgreSQL]
        SQLite[SQLite (dev)]
        Redis[Redis]
        FAISS[FAISS]
        VectorEngine[Vector Search]
    end

    subgraph "New Integrations"
        Kubernetes[Kubernetes]
        Terraform[Terraform]
        Helm[Helm]
        Prometheus[Prometheus]
        Grafana[Grafana]
        Istio[Istio Service Mesh]
    end

    FastAPI --> Kubernetes
    React --> Kubernetes
    PostgreSQL --> Kubernetes
    Redis --> Kubernetes
    FAISS --> Kubernetes
    
    FastAPI --> Prometheus
    PostgreSQL --> Prometheus
    
    FastAPI --> Grafana
    Prometheus --> Grafana
    Loki --> Grafana
    
    FastAPI --> Istio
    PostgreSQL --> Istio
```

## Performance Optimization Strategies

### Database Query Optimization

```python
# Optimized search query
async def search_documents(db, query: str, user_id: int):
    sql = """
        SELECT d.*, ts_rank_cd(to_tsvector('english', d.content), 
                               to_tsquery(%s)) as score
        FROM documents d
        WHERE to_tsvector('english', d.content) @@ to_tsquery(%s)
          AND d.user_id = %s
          AND d.created_at > NOW() - INTERVAL '30 days'
        ORDER BY score DESC
        LIMIT 20
    """
    return await db.fetch(sql, query, query, user_id)
```

### Caching Strategy

```python
# Cache key patterns
CACHE_KEYS = {
    "search_results": "search:results:{query_hash}:{page}",
    "document_metadata": "doc:metadata:{doc_id}",
    "user_preferences": "user:preferences:{user_id}",
    "search_suggestions": "search:suggestions:{query_prefix}",
}

# Cache TTLs
CACHE_TTLS = {
    "search_results": 300,      # 5 minutes
    "document_metadata": 3600,  # 1 hour
    "user_preferences": 86400,  # 24 hours
    "search_suggestions": 300,  # 5 minutes
}
```

## Deployment Strategy

### Blue-Green Deployment

```yaml
# Kubernetes blue-green deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nebula-backend-blue
  labels:
    version: v1.0.0
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nebula-backend-green
  labels:
    version: v2.0.0
---
apiVersion: v1
kind: Service
metadata:
  name: nebula-backend
spec:
  selector:
    version: v1.0.0  # Switch to v2.0.0 for cutover
  ports:
  - port: 8000
```

### CI/CD Pipeline

```yaml
# GitHub Actions CI/CD
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: pytest --cov
    - name: Security scan
      run: bandit -r backend/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      run: |
        docker build -t nebula/backend:${{ github.sha }} .
        docker push nebula/backend:${{ github.sha }}
    - name: Deploy to Kubernetes
      run: |
        helm upgrade nebula ./helm/nebula \
          --set backend.image.tag=${{ github.sha }} \
          --namespace production
```

## Summary of Technical Decisions

### Key Decisions

1. **Container Orchestration**: Kubernetes with Helm for declarative, version-controlled deployments

2. **Security Architecture**: Zero Trust with mTLS, JWT authentication, RBAC, and comprehensive audit logging

3. **Performance Optimization**: Multi-layer caching (CDN, Redis, query caching) with performance baselines

4. **Observability**: Full-stack monitoring with Prometheus, Grafana, Loki, and Jaeger

5. **Data Integrity**: AES-256 encryption at rest, TLS 1.3 in transit, with automatic secret rotation

6. **Compliance**: Built-in GDPR, CCPA, and OWASP compliance with data retention policies

7. **Infrastructure as Code**: Terraform for cloud infrastructure, Helm for Kubernetes, GitOps workflow

8. **Zero-Downtime Deployments**: Blue-green deployments with automated rollback

### Architecture Trade-offs

| Trade-off | Decision | Rationale |
|-----------|----------|-----------|
| Microservices vs Monolith | Monolith with internal workers | Reduce operational complexity |
| Centralized vs Distributed | Centralized auth, distributed workers | Balance consistency and scalability |
| Real-time vs Batch | Hybrid approach | Cost optimization |
| Open-source vs Commercial | Open-source stack | Cost and flexibility |
| Manual vs Automated | Fully automated | Reliability and consistency |

### Next Steps

1. Implement audit logging for all security events
2. Configure Kubernetes RBAC and network policies
3. Set up CI/CD pipelines with security scans
4. Configure monitoring and alerting rules
5. Implement automated backup and disaster recovery
6. Conduct security audit and penetration testing
7. Load testing and performance optimization
8. Documentation and training

## Architecture

### System Architecture Layers

The architecture follows a layered approach with clear separation of concerns:

#### 1. Client Layer
- Web Browser: React single-page application
- Mobile Application: Native mobile clients
- API Consumer: Third-party integrations

#### 2. Edge Layer
- CDN: CloudFront/Cloudflare for static asset delivery
- WAF: Web Application Firewall with OWASP rules
- Load Balancer: Nginx ingress for traffic distribution

#### 3. Gateway Layer
- API Gateway: Centralized authentication, rate limiting, and routing
- Service Mesh: Mutual TLS, distributed tracing, and circuit breaking

#### 4. Application Layer
- FastAPI Backend: RESTful API with async I/O
- React Frontend: Client-side rendered application
- Vector Worker: Asynchronous vector embedding processing
- Index Worker: Document indexing and search optimization

#### 5. Data Layer
- PostgreSQL: Primary database with connection pooling
- Redis: Distributed cache and session store
- FAISS: Vector similarity search index
- MinIO: Object storage for document files

#### 6. Observability Layer
- Prometheus: Metrics collection and storage
- Grafana: Visualization dashboards
- AlertManager: Alert routing and notification
- Loki: Log aggregation
- Jaeger: Distributed tracing

### Data Flow Patterns

**Request Flow**: Client → CDN/WAF → Ingress → Service Mesh → Gateway → Backend → [Redis/PostgreSQL/Vector Search]

**Async Processing Flow**: Backend → Redis Streams → Worker Services → PostgreSQL

**Event-Driven Flow**: Services → Event Bus → Consumer Services

## Components and Interfaces

### Service Components

#### 1. Backend Service (FastAPI)
**Port**: 8000

**Key Interfaces**:
- `/api/v1/auth/*` - Authentication endpoints
- `/api/v1/search` - Search query endpoints
- `/api/v1/documents/*` - Document management
- `/api/v1/vector/*` - Vector operations
- `/health/*` - Health check endpoints

**Dependencies**:
- PostgreSQL (primary database)
- Redis (caching/sessions)
- Vector Search API (for embeddings)
- External search APIs (Brave, SerpAPI)

#### 2. Frontend Service (React)
**Port**: 3000 (development), 80 (production via nginx)

**Key Interfaces**:
- `/` - Dashboard
- `/search?q={query}` - Search results
- `/documents/*` - Document management
- `/settings/*` - User settings

**Dependencies**:
- Backend API (all endpoints)
- CDN (static assets)
- Redis (session validation)

#### 3. Vector Worker Service
**Port**: 8001

**Key Interfaces**:
- `POST /process` - Process vector embeddings
- `POST /index` - Update vector index
- `GET /status` - Processing status

**Dependencies**:
- FAISS (vector index)
- PostgreSQL (metadata)
- OpenAI/Ollama API (embeddings)

#### 4. Index Worker Service
**Port**: 8002

**Key Interfaces**:
- `POST /index` - Start indexing job
- `GET /jobs/{id}` - Job status
- `POST /cancel` - Cancel job

**Dependencies**:
- PostgreSQL (job tracking)
- MinIO (document storage)
- Vector Worker (semantic processing)

### Inter-Service Communication

#### Sync Communication (HTTP/2)
- Backend ↔ Frontend (API requests)
- Backend ↔ PostgreSQL (queries)
- Backend ↔ Redis (cache ops)
- Backend ↔ Vector Worker (async processing)

#### Async Communication (Redis Streams)
- Backend → Index Worker (document.uploaded events)
- Vector Worker → Index Worker (vector.indexed events)
- Backend → Notification Service (user notifications)

### API Contracts

#### Search Query Request/Response
```json
// Request
GET /api/v1/search?q=neural+networks&page=1&limit=20

// Response (200 OK)
{
  "data": {
    "results": [...],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "cache_hit": false,
    "duration_ms": 45
  }
}
```

#### Document Upload Request/Response
```json
// Request
POST /api/v1/documents/upload
Content-Type: multipart/form-data

// Response (202 Accepted)
{
  "data": {
    "document_id": "doc_123",
    "status": "processing",
    "progress_url": "/api/v1/documents/doc_123/status"
  }
}
```

## Data Models

### Core Database Schema

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Documents Table
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    file_path VARCHAR(1000),
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, indexed, failed
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Search History Table
```sql
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query TEXT NOT NULL,
    results_count INTEGER,
    source VARCHAR(50), -- web_search, document_search, vector_search
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Terms and Conditions Tables
```sql
CREATE TABLE terms_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    requires_acceptance BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE user_terms_acceptances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    terms_version_id INTEGER REFERENCES terms_versions(id),
    accepted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);
```

#### Cookie Consent Table
```sql
CREATE TABLE cookie_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN DEFAULT TRUE,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(20), -- success, failure
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Redis Data Structures

#### Session Cache
```python
# Key: session:{user_id}
# Type: Hash
# Fields: token, refresh_token, expires_at, permissions
```

#### Search Results Cache
```python
# Key: search:results:{query_hash}:{page}
# Type: String (JSON)
# TTL: 300 seconds (5 minutes)
```

#### Document Metadata Cache
```python
# Key: doc:metadata:{doc_id}
# Type: Hash
# Fields: title, file_type, status, created_at
# TTL: 3600 seconds (1 hour)
```

### Vector Index Structure

```python
# FAISS Index Format
{
    "index_type": "IVFFlat",
    "dimension": 768,  # BERT base dimension
    "nlist": 100,      # Number of clusters
    "metric_type": "IP",  # Inner product for similarity
    "vectors": [...],    # Embedded document vectors
    "metadata": [...]    # Document IDs mapping
}
```

## Correctness Properties

### 1. Security Correctness Properties

**Property 1.1: Authentication Integrity**
- All authenticated endpoints must validate JWT tokens before processing
- Expired or invalid tokens must be rejected with HTTP 401
- Token refresh mechanism must work correctly for valid sessions

**Property 1.2: Access Control Enforcement**
- Users can only access their own documents
- Admin users can access all documents
- Role-based permissions must be checked on every request

**Property 1.3: Data Encryption**
- All sensitive fields must be encrypted at rest using AES-256
- Encryption keys must be rotated periodically
- Decryption must only occur within authorized services

### 2. Data Consistency Properties

**Property 2.1: Search Index Consistency**
- Document updates must be reflected in search results within 60 seconds
- Deleted documents must be removed from search index
- Vector embeddings must be updated when document content changes

**Property 2.2: Cache Coherency**
- Cache invalidation must occur on document updates
- Stale data must not be served from cache
- Cache hit rate must be tracked and monitored

### 3. Performance Correctness Properties

**Property 3.1: Search Latency**
- P95 search latency must be under 200ms for cached queries
- P95 search latency must be under 500ms for uncached queries
- Query timeouts must be enforced and graceful degradation applied

**Property 3.2: System Availability**
- System must maintain 99.9% uptime (SLO)
- Graceful degradation must be implemented for non-critical dependencies
- Circuit breakers must prevent cascading failures

### 4. Data Integrity Properties

**Property 4.1: Transaction Atomicity**
- Document upload must create database record and storage entry atomically
- Search history must be recorded consistently
- Cookie consent preferences must persist across sessions

**Property 4.2: Data Retention Enforcement**
- Search history older than 90 days must be automatically deleted
- User sessions must expire after configured TTL
- Audit logs must be retained for 365 days

## Error Handling

### Error Classification

#### 1. Client Errors (4xx)
- **400 Bad Request**: Invalid input, missing required fields
- **401 Unauthorized**: Invalid or expired authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource does not exist
- **429 Too Many Requests**: Rate limit exceeded

#### 2. Server Errors (5xx)
- **500 Internal Server Error**: Unexpected server error
- **502 Bad Gateway**: Upstream service unavailable
- **503 Service Unavailable**: Service overloaded or degraded
- **504 Gateway Timeout**: Upstream service timeout

### Error Handling Patterns

#### 1. Validation Errors
```python
class ValidationError(Exception):
    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(message)
```

#### 2. Authentication Errors
```python
class AuthenticationError(Exception):
    def __init__(self, message: str = "Authentication required"):
        self.message = message
        super().__init__(message)
```

#### 3. Rate Limiting Errors
```python
class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")
```

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "field": "email",
    "details": {
      "expected": "user@example.com",
      "received": "invalid-email"
    },
    "request_id": "abc123"
  }
}
```

### Retry Strategy

#### Exponential Backoff
```python
# Retry configuration
RETRY_CONFIG = {
    "max_attempts": 3,
    "base_delay": 100,      # ms
    "max_delay": 10000,     # ms
    "backoff_multiplier": 2,
    "retryable_status_codes": [502, 503, 504]
}
```

#### Circuit Breaker
```python
# Circuit breaker settings
CIRCUIT_BREAKER = {
    "failure_threshold": 5,
    "success_threshold": 2,
    "timeout": 30,          # seconds
    "half_open_max_calls": 3
}
```

### Logging and Monitoring

#### Error Logging Standards
- All errors must be logged with error level
- Error logs must include request_id for correlation
- Sensitive data must be masked in error messages
- Stack traces must be captured for debugging

#### Alerting Thresholds
- Error rate > 1% over 5 minutes triggers critical alert
- Service unavailability triggers immediate critical alert
- Database connection pool exhaustion triggers warning alert

## Testing Strategy

### Test Pyramid

```
    /\
   /  \     Integration Tests (10%)
  /----\
 /      \  Unit Tests (70%)
/--------\
  E2E Tests (20%)
```

### Unit Testing

#### Test Coverage Requirements
- **Minimum Coverage**: 80% for all services
- **Critical Paths**: 100% coverage for security and authentication
- **Edge Cases**: All boundary conditions and error scenarios

#### Test Framework
- **Backend**: pytest with pytest-asyncio
- **Frontend**: Vitest with React Testing Library
- **Vector Search**: pytest with FAISS fixtures

#### Example Test Structure
```python
# backend/tests/test_authentication.py
import pytest

class TestAuthentication:
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self):
        # Given valid credentials
        # When user attempts to login
        # Then access token is generated
        
    @pytest.mark.asyncio
    async def test_login_with_invalid_password(self):
        # Given invalid password
        # When user attempts to login
        # Then authentication error is returned
```

### Integration Testing

#### Test Scenarios
1. **Full Authentication Flow**: Login → Token refresh → Logout
2. **Search Flow**: Query → Results → Cache hit/miss
3. **Document Upload Flow**: Upload → Processing → Indexed
4. **Cross-Service Communication**: Backend ↔ Vector Worker ↔ Index Worker

#### Test Framework
- **Backend**: pytest with docker-compose fixtures
- **Frontend**: Playwright for browser integration
- **API Contracts**: Pact for consumer-driven contracts

### End-to-End Testing

#### Test Scenarios
1. **User Registration**: Signup → Email verification → Login → Dashboard
2. **Document Search**: Upload → Search → Results → View → Download
3. **Rate Limiting**: Exceed rate limit → Receive 429 → Retry after timeout
4. **Error Recovery**: Simulate service failure → Verify graceful degradation

#### Test Framework
- **E2E Tests**: Playwright with TypeScript
- **Test Data**: Test containers and local test fixtures
- **Parallel Execution**: 4 parallel workers for faster execution

### Performance Testing

#### Load Testing
- **Tool**: Locust
- **Concurrency**: 10,000 concurrent users
- **Duration**: 30 minutes per scenario
- **Metrics**: Response time, throughput, error rate

#### Stress Testing
- **Goal**: Identify breaking point
- **Method**: Gradually increase load until failure
- **Recovery**: Verify graceful degradation and recovery

### Security Testing

#### Automated Scans
- **Static Analysis**: Bandit (Python), ESLint (Frontend)
- **Dependency Scanning**: Safety, npm audit
- **Secrets Detection**: Git-secrets, truffleHog

#### Manual Penetration Testing
- **OWASP Top 10**: Quarterly penetration testing
- **SQL Injection**: Parameterized query validation
- **XSS Prevention**: Input sanitization verification
- **CSRF Protection**: Token validation testing

### Test Data Management

#### Test Fixtures
- **Common Fixtures**: Users, documents, search queries
- **Test Databases**: Isolated test databases per test run
- **Sample Data**: Realistic but non-sensitive test data

#### CI/CD Integration
- **Test on Push**: Run unit and integration tests
- **Test on PR**: Run full test suite with coverage
- **Test on Merge**: Run E2E and performance tests
- **Coverage Reporting**: Generate and publish coverage reports

### Regression Testing

#### Automated Regression Suite
- **Core Flows**: Authentication, search, document management
- **Security Paths**: Login, access control, encryption
- **Performance Baselines**: Verify performance regression

#### Regression Trigger
- All changes to core modules
- Database schema changes
- API contract modifications

### Continuous Testing

#### Quality Gates
1. **Pre-commit**: Lint and unit tests
2. **PR Creation**: Full test suite with coverage
3. **Merge to Main**: E2E and performance tests
4. **Production Deployment**: Smoke tests and health checks

#### Test Metrics
- **Test Execution Time**: < 10 minutes for full suite
- **Flaky Test Rate**: < 1% of tests
- **Coverage**: > 80% for all services
## Components and Interfaces

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Edge Layer (Ingress/CDN)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │   Nginx      │  │     CDN      │  │     WAF      │                    │
│  │  Ingress     │  │  CloudFront  │  │  OWASP Rules │                    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                    │
│         │                 │                 │                             │
└─────────┼─────────────────┼─────────────────┼─────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Gateway Layer                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    API Gateway                                    │  │
│  │  - JWT Validation                                                 │  │
│  │  - Rate Limiting                                                  │  │
│  │  - Request Routing                                                │  │
│  │  - Version Management (/api/v1/, /api/v2/)                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    Service Mesh (Istio)                           │  │
│  │  - mTLS Encryption                                                │  │
│  │  - Circuit Breaking                                               │  │
│  │  - Distributed Tracing                                            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                         │                 │
                         ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Application Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Backend    │  │   Frontend   │  │ VectorWorker │  │ IndexWorker│ │
│  │  (FastAPI)   │  │  (React)     │  │    (Python)  │  │  (Python)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘ │
│         │                 │                 │                 │          │
│         ▼                 ▼                 ▼                 ▼          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Event Bus (Redis Streams)                    │   │
│  │  - document.uploaded  - document.indexed  - indexing.failed     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Layer                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │    FAISS     │  │   MinIO    │ │
│  │  (Primary DB)│  │  (Cache)     │  │ (Vector)     │  │ (Storage)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Interfaces

#### Backend-to-Frontend API
- **Authentication**: JWT tokens with refresh
- **Search API**: `/api/v1/search` (POST, GET)
- **Documents**: `/api/v1/documents` (CRUD operations)
- **Notifications**: `/api/v1/notifications` (WebSockets)

#### Backend-to-Database
- **Connection Pool**: 10-50 connections based on load
- **Encryption**: TLS 1.3 for PostgreSQL connections
- **Query Timeout**: 5 seconds for search queries

#### Backend-to-External Services
- **Vector Worker**: HTTP/2 with 30-second timeout
- **AI Provider**: Async calls with retry logic
- **Storage**: Signed URLs with 1-hour expiration

#### Cross-Service Communication
- **Protocol**: JSON over HTTP/2
- **Authentication**: Short-lived JWT tokens (5 minutes)
- **Timeout**: 10 seconds for service calls
- **Retry**: Exponential backoff (max 3 retries)

## Data Models

### Core Entities

```python
# User Model
{
    "id": "uuid",
    "email": "string (unique)",
    "password_hash": "string",
    "first_name": "string",
    "last_name": "string",
    "is_active": "boolean",
    "is_verified": "boolean",
    "is_mfa_enabled": "boolean",
    "created_at": "datetime",
    "updated_at": "datetime",
    "last_login": "datetime",
    "mfa_secret": "string (encrypted)",
    "oauth_providers": ["string"]
}

# Document Model
{
    "id": "uuid",
    "user_id": "uuid",
    "title": "string",
    "description": "text",
    "file_path": "string",
    "file_size": "integer",
    "file_type": "string",
    "status": "string (uploading|indexed|error)",
    "content": "text",
    "metadata": "json",
    "created_at": "datetime",
    "updated_at": "datetime",
    "deleted_at": "datetime",
    "retention_until": "datetime"
}

# Search History Model
{
    "id": "uuid",
    "user_id": "uuid",
    "query": "string",
    "results_count": "integer",
    "searched_at": "datetime",
    "device_info": "json",
    "ip_address": "string"
}

# Terms Version Model
{
    "id": "uuid",
    "version": "string",
    "title": "string",
    "content": "text",
    "effective_date": "datetime",
    "created_at": "datetime",
    "created_by": "uuid"
}

# Privacy Policy Model
{
    "id": "uuid",
    "version": "string",
    "title": "string",
    "content": "text",
    "effective_date": "datetime",
    "created_at": "datetime",
    "created_by": "uuid"
}

# Cookie Consent Model
{
    "id": "uuid",
    "user_id": "uuid",
    "consent_given": "boolean",
    "consent_categories": ["essential", "analytics", "marketing"],
    "consented_at": "datetime",
    "ip_address": "string",
    "user_agent": "string"
}

# Audit Log Model
{
    "id": "uuid",
    "event_type": "string",
    "user_id": "uuid",
    "ip_address": "string",
    "user_agent": "string",
    "entity_type": "string",
    "entity_id": "uuid",
    "action": "string",
    "details": "json",
    "created_at": "datetime"
}

# Encryption Key Model
{
    "id": "uuid",
    "key_id": "string",
    "key_version": "integer",
    "algorithm": "string",
    "created_at": "datetime",
    "rotated_at": "datetime",
    "is_active": "boolean"
}
```

### Database Schema Updates

**New Tables:**
- `terms_versions` - Terms of Service versions
- `privacy_policies` - Privacy Policy versions
- `cookie_consents` - User cookie preferences
- `audit_logs` - Security event logging
- `encryption_keys` - Data encryption key management
- `service_tokens` - Cross-service authentication tokens
- `api_gateway_logs` - Gateway request logging

**Enhanced Tables:**
- `users` - Add MFA fields, OAuth providers
- `documents` - Add encryption flags, retention fields
- `search_logs` - Add device info, results count

## Correctness Properties

### Security Properties

1. **Authentication Integrity**: All JWT tokens must be valid, not expired, and signed with the correct key
2. **Authorization Enforcement**: No request can access data without proper RBAC permissions
3. **Data Encryption**: All sensitive fields must be encrypted using AES-256 before storage
4. **Input Sanitization**: All user input must be sanitized to prevent XSS and injection attacks
5. **Rate Limiting**: Requests must be throttled according to configured limits

### Performance Properties

1. **Search Latency**: P95 search latency must be under 200ms under normal load
2. **Cache Hit Rate**: Redis cache must achieve 95%+ hit rate for search results
3. **Database Connection**: Connection pool must not exceed 80% utilization
4. **API Response**: All API endpoints must respond in under 500ms at P95

### Compliance Properties

1. **Data Retention**: Search history must be deleted after 90 days automatically
2. **Audit Logging**: All security events must be logged within 1 second of occurrence
3. **GDPR Compliance**: User data deletion requests must be fulfilled within 30 days
4. **Cookie Consent**: Non-essential cookies must not be set without user consent

### Reliability Properties

1. **Health Checks**: All services must respond to health checks within 10 seconds
2. **Failover**: Primary database failover must complete within 60 seconds
3. **Backup Integrity**: All backups must pass integrity checks before confirmation
4. **Service Availability**: System must maintain 99.9% availability (max 8.76 hours downtime/year)

## Error Handling

### Error Categories

1. **Authentication Errors (401, 403)**
   - Invalid JWT token
   - Expired refresh token
   - MFA verification required
   - Account locked

2. **Validation Errors (400)**
   - Invalid input format
   - Required field missing
   - Invalid search query syntax

3. **Rate Limiting Errors (429)**
   - Too many requests
   - Burst limit exceeded

4. **Data Errors (404, 500)**
   - Resource not found
   - Database connection failed
   - Indexing error

5. **External Service Errors (502, 503)**
   - Vector worker unavailable
   - AI provider timeout
   - Storage service down

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid search query format",
    "details": {
      "field": "query",
      "reason": "Contains invalid characters"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_1234567890abcdef"
  }
}
```

### Error Recovery Strategies

1. **Database Connection Failure**
   - Retry with exponential backoff (max 3 retries)
   - Fail over to replica if available
   - Alert on sustained failures

2. **External Service Timeout**
   - Return cached results if available
   - Queue request for retry
   - Notify operations team

3. **Rate Limiting**
   - Return 429 with retry-after header
   - Log rate limit event for analysis
   - Gradually increase limits based on abuse patterns

## Testing Strategy

### Test Categories

1. **Unit Tests**
   - Test individual functions and classes
   - Target: 80%+ code coverage
   - Tools: pytest, unittest, pytest-asyncio

2. **Integration Tests**
   - Test component interactions
   - Test database connections
   - Test external service calls

3. **Security Tests**
   - OWASP ZAP vulnerability scanning
   - Penetration testing
   - Security header validation

4. **Performance Tests**
   - Load testing with Locust (10,000 concurrent users)
   - Stress testing to identify breaking points
   - Baseline measurements for regression detection

5. **E2E Tests**
   - Full user journeys
   - CI/CD pipeline validation
   - Browser automation with Playwright

### Test Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Test Environment Pyramid                          │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  ���                     E2E Tests (100 tests)                     │  │
│  │  - Full user journeys                                          │  │
│  │  - CI/CD pipeline validation                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Integration Tests (500 tests)                │  │
│  │  - Component interactions                                      │  │
│  │  - Database connections                                        │  │
│  └────────────────────────────────────��──────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   Unit Tests (2000 tests)                     │  │
│  │  - Individual functions                                        │  │
│  │  - Edge cases and error handling                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Security Testing Checklist

- [ ] SQL injection prevention
- [ ] XSS attack prevention
- [ ] CSRF token validation
- [ ] JWT token security
- [ ] Password hashing strength
- [ ] Rate limiting effectiveness
- [ ] CORS configuration
- [ ] Security headers presence
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Audit logging completeness
- [ ] Secret management security

### Performance Testing Checklist

- [ ] Search latency under 200ms P95
- [ ] API response under 500ms P95
- [ ] Database queries under 100ms P95
- [ ] Cache hit rate above 95%
- [ ] Concurrent user support (10,000)
- [ ] Load balancing distribution
- [ ] Connection pool efficiency
- [ ] Memory usage under 80%

This design provides a comprehensive foundation for implementing production infrastructure, security hardening, system integration, and performance optimization for the Nebula Search Engine.
## Correctness Properties

### Security Properties

**Property 1**: Authentication Integrity
All JWT tokens must be valid, not expired, and signed with the correct key
- Verification: Token validation middleware checks signature, expiry, and revocation list
- Testing: Unit tests for JWT validation with various token states

**Property 2**: Authorization Enforcement
No request can access data without proper RBAC permissions
- Verification: RBAC middleware checks user role against endpoint permissions
- Testing: Integration tests with different user roles accessing protected resources

**Property 3**: Data Encryption
All sensitive fields must be encrypted using AES-256 before storage
- Verification: Field-level encryption middleware intercepts sensitive data
- Testing: Unit tests verifying encryption before database write

**Property 4**: Input Sanitization
All user input must be sanitized to prevent XSS and injection attacks
- Verification: Input sanitization middleware scans all user input
- Testing: Fuzz tests with malicious input patterns

**Property 5**: Rate Limiting
Requests must be throttled according to configured limits
- Verification: Rate limiter middleware checks request frequency
- Testing: Stress tests exceeding rate limits

### Performance Properties

**Property 6**: Search Latency
P95 search latency must be under 200ms under normal load
- Verification: Load testing with 10,000 concurrent users
- Testing: Locust load tests measuring latency percentiles

**Property 7**: Cache Hit Rate
Redis cache must achieve 95%+ hit rate for search results
- Verification: Cache metrics in Prometheus monitoring
- Testing: Load tests measuring cache effectiveness

**Property 8**: Database Connection
Connection pool must not exceed 80% utilization
- Verification: Database connection pool metrics
- Testing: Stress tests pushing connection pool to limits

### Compliance Properties

**Property 9**: Data Retention
Search history must be deleted after 90 days automatically
- Verification: Scheduled cleanup job runs daily
- Testing: Data retention tests verifying deletion

**Property 10**: Audit Logging
All security events must be logged within 1 second of occurrence
- Verification: Logging middleware timestamps all security events
- Testing: Log delivery latency tests

### Reliability Properties

**Property 11**: Health Checks
All services must respond to health checks within 10 seconds
- Verification: Kubernetes liveness probes configured
- Testing: Service mesh health check validation

**Property 12**: Failover
Primary database failover must complete within 60 seconds
- Verification: Automated failover testing in staging
- Testing: Chaos engineering tests simulating database failure

## Error Handling

### Error Categories

1. **Authentication Errors (401, 403)**
   - Invalid JWT token
   - Expired refresh token
   - MFA verification required
   - Account locked

2. **Validation Errors (400)**
   - Invalid input format
   - Required field missing
   - Invalid search query syntax

3. **Rate Limiting Errors (429)**
   - Too many requests
   - Burst limit exceeded

4. **Data Errors (404, 500)**
   - Resource not found
   - Database connection failed
   - Indexing error

5. **External Service Errors (502, 503)**
   - Vector worker unavailable
   - AI provider timeout
   - Storage service down

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid search query format",
    "details": {
      "field": "query",
      "reason": "Contains invalid characters"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_1234567890abcdef"
  }
}
```

### Error Recovery Strategies

1. **Database Connection Failure**
   - Retry with exponential backoff (max 3 retries)
   - Fail over to replica if available
   - Alert on sustained failures

2. **External Service Timeout**
   - Return cached results if available
   - Queue request for retry
   - Notify operations team

3. **Rate Limiting**
   - Return 429 with retry-after header
   - Log rate limit event for analysis
   - Gradually increase limits based on abuse patterns

## Testing Strategy

### Test Categories

1. **Unit Tests**
   - Test individual functions and classes
   - Target: 80%+ code coverage
   - Tools: pytest, unittest, pytest-asyncio

2. **Integration Tests**
   - Test component interactions
   - Test database connections
   - Test external service calls

3. **Security Tests**
   - OWASP ZAP vulnerability scanning
   - Penetration testing
   - Security header validation

4. **Performance Tests**
   - Load testing with Locust (10,000 concurrent users)
   - Stress testing to identify breaking points
   - Baseline measurements for regression detection

5. **E2E Tests**
   - Full user journeys
   - CI/CD pipeline validation
   - Browser automation with Playwright

### Test Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Test Environment Pyramid                          │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     E2E Tests (100 tests)                     │  │
│  │  - Full user journeys                                          │  │
│  │  - CI/CD pipeline validation                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Integration Tests (500 tests)                │  │
│  │  - Component interactions                                      │  │
│  │  - Database connections                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   Unit Tests (2000 tests)                     │  │
│  │  - Individual functions                                        │  │
│  │  - Edge cases and error handling                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Security Testing Checklist

- [ ] SQL injection prevention
- [ ] XSS attack prevention
- [ ] CSRF token validation
- [ ] JWT token security
- [ ] Password hashing strength
- [ ] Rate limiting effectiveness
- [ ] CORS configuration
- [ ] Security headers presence
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Audit logging completeness
- [ ] Secret management security

### Performance Testing Checklist

- [ ] Search latency under 200ms P95
- [ ] API response under 500ms P95
- [ ] Database queries under 100ms P95
- [ ] Cache hit rate above 95%
- [ ] Concurrent user support (10,000)
- [ ] Load balancing distribution
- [ ] Connection pool efficiency
- [ ] Memory usage under 80%

---

This design provides a comprehensive foundation for implementing production infrastructure, security hardening, system integration, and performance optimization for the Nebula Search Engine.