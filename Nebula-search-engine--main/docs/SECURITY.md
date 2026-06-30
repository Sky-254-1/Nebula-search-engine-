# Security Policy and Documentation

## Overview

Nebula Search Engine is built with a defense-in-depth security architecture. This document describes the security mechanisms in place across authentication, authorization, data protection, API security, and operational security.

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Network Security                             │
│  HTTPS/TLS · Nginx reverse proxy · DDoS protection              │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    API Security Layer                             │
│  CORS · CSP · HSTS · CSRF tokens · Rate limiting · XSS filters  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                  Authentication & Session Layer                   │
│  JWT (HS256) · Refresh tokens · 2FA/TOTP · WebAuthn · Cookies   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                   Authorization Layer                             │
│  RBAC (user/admin) · Rate limit tiers · Role-based route guards  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     Data Security Layer                           │
│  Encryption at rest · PBKDF2/bcrypt hashing · Secure key storage │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### JWT (JSON Web Tokens)

Access tokens are JWT-encoded with HS256 signing. The token payload contains the user's email, role, and token type.

| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Signing key | `JWT_SECRET` (64-char hex) |
| Access token expiry | Configurable via `JWT_EXPIRY_HOURS` (default: 24h) |
| Refresh token expiry | Configurable via `REFRESH_TOKEN_DAYS` (default: 30d) |
| Token type claim | `"type": "access"` or `"type": "refresh"` |

Access tokens are validated on every authenticated request. The `get_current_user` dependency decodes the JWT, verifies the signature, checks expiry, and extracts the user email.

### Refresh Token Rotation

Refresh tokens use a random URL-safe token (48 bytes) stored as a SHA-256 hash in the database. On refresh:

1. The incoming refresh token is hashed and looked up in the `sessions` table
2. The session is validated (not revoked, not expired, not rotated)
3. A new access token and a new refresh token are issued
4. The old session is marked as rotated
5. A new session row is created for the new refresh token

If a rotated refresh token is reused, it triggers a security alert (potential token theft) and all sessions for that user are revoked.

### Session Management

- Sessions are stored in the `sessions` database table
- Each session tracks: user, refresh token hash, creation time, expiry, rotation status
- Sessions can be revoked individually or en masse
- Refresh token reuse detection with automatic session family revocation
- Configurable via `ENABLE_REFRESH_REUSE_DETECTION`

### Cookie-Based Auth Mode

When `AUTH_COOKIE_MODE=true` (default), tokens are stored in HTTP-only cookies:

| Cookie | Type | HttpOnly | Secure | SameSite |
|--------|------|----------|--------|----------|
| `access_token` | HTTP-only | Yes | Configurable (`COOKIE_SECURE`) | Configurable (`COOKIE_SAMESITE`) |
| `refresh_token` | HTTP-only | Yes | Configurable | Configurable |
| `csrf_token` | HTTP-only | Yes | Configurable | Configurable |

When `AUTH_COOKIE_MODE=false`, tokens are returned in the response body and must be sent via `Authorization: Bearer <token>` headers.

---

## Authorization

### RBAC (Role-Based Access Control)

Two roles are supported:

| Role | Default | Permissions |
|------|---------|-------------|
| `user` | Yes | Search, AI answers, document storage, vector search, own history, own settings |
| `admin` | No | All user permissions + audit logs, session management, user role management |

The `require_admin` dependency guard checks the JWT payload's `role` claim and rejects non-admin requests with HTTP 403.

### Rate Limit Tiers

Requests are limited per user or per IP based on the user's tier:

| Tier | Requests/min | Default Assignee |
|------|-------------|------------------|
| `basic` | 30 | Default user |
| `pro` | 120 | Upgraded users |
| `enterprise` | 600 | Enterprise users |

Burst allowance multiplies the base rate by `RATE_LIMIT_BURST_MULTIPLIER` (default: 2x) over a 2-second window.

---

## Password Policy

### Requirements

- Minimum length: **8 characters**
- Maximum length: **128 characters**
- Must include at least one uppercase letter (`[A-Z]`)
- Must include at least one lowercase letter (`[a-z]`)
- Must include at least one digit (`[0-9]`)
- Must include at least one special character (`[!@#$%^&*(),.?":{}|<>]`)
- Must not match the user's email address
- Must not be in the common passwords list

### Hashing

| Algorithm | Iterations | Salt | Format | Status |
|-----------|-----------|------|--------|--------|
| **bcrypt** | 12 rounds | 16-byte random | bcrypt hash string | Current (v1.1+) |
| PBKDF2-SHA256 | 200,000 | 16-byte random hex | `{salt}${hash}` | Legacy fallback |

The system uses bcrypt for new passwords while maintaining backward compatibility with existing PBKDF2-SHA256 hashes. Verification checks the hash format and dispatches to the correct algorithm.

### Brute-Force Protection

- Per-IP+email attempt counter stored in cache (3600s TTL)
- Account lockout after `MAX_LOGIN_ATTEMPTS` (default: 5) failures
- Lockout duration: `LOGIN_LOCKOUT_MINUTES` (default: 15)
- Exponential delay between attempts: 1s, 2s, 4s, 8s, 15s

---

## Two-Factor Authentication (2FA)

### TOTP Implementation

When `ENABLE_2FA=true`:

1. User enables 2FA via settings → generates a TOTP secret
2. Secret is displayed as a QR code for authenticator apps (Google Authenticator, Authy, etc.)
3. User verifies by submitting a valid TOTP code
4. On subsequent logins, after password verification, the user must provide a TOTP code
5. TOTP codes are valid for 30 seconds with a 3-step window (90s drift tolerance)

**Configuration:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_2FA` | `false` | Enable TOTP 2FA globally |
| `TOTP_ISSUER` | `Nebula Search` | Issuer label in authenticator app |

### WebAuthn / Passkeys

When `ENABLE_WEBAUTHN=true`, passwordless authentication via WebAuthn (passkeys) is supported for supported browsers and platforms.

---

## API Security

### CORS (Cross-Origin Resource Sharing)

Configured via `CORS_ORIGINS` — a comma-separated list of allowed origins. In production, restrict to your frontend domain only.

| Method | Value |
|--------|-------|
| Allowed origins | `CORS_ORIGINS` env var |
| Allow credentials | `true` |
| Allowed methods | `GET`, `POST`, `DELETE`, `OPTIONS`, `PUT`, `PATCH` |
| Allowed headers | `Authorization`, `Content-Type`, `X-CSRF-Token`, `X-Request-ID` |

### CSP (Content Security Policy)

All CSP directives are configurable via environment variables:

| Directive | Env Variable | Default |
|-----------|-------------|---------|
| `default-src` | `CSP_DEFAULT_SRC` | `'self'` |
| `script-src` | `CSP_SCRIPT_SRC` | `'self'` |
| `style-src` | `CSP_STYLE_SRC` | `'self' 'unsafe-inline'` |
| `img-src` | `CSP_IMG_SRC` | `'self' data: https:` |
| `connect-src` | `CSP_CONNECT_SRC` | `'self'` |
| `font-src` | `CSP_FONT_SRC` | `'self'` |
| `frame-src` | `CSP_FRAME_SRC` | `'none'` |
| `object-src` | `CSP_OBJECT_SRC` | `'none'` |

### Rate Limiting

| Endpoint | Rate Limit | Scope |
|----------|-----------|-------|
| Signup | `SIGNUP_RATE_LIMIT` (default: 5/min) | IP-based |
| Login | `LOGIN_RATE_LIMIT` (default: 5/min) | IP-based |
| Token refresh | `REFRESH_RATE_LIMIT` (default: 10/min) | IP-based |
| General API | Tier-based (30/120/600 per min) | User or IP |
| Burst | 2x steady-state over 2s window | Per-scope |

Rate limiting uses Redis when available (fallback to in-memory). The `SlowAPI` middleware provides additional rate-limit decorators.

### CSRF Protection

When `ENABLE_CSRF=true` (default), the double-submit cookie pattern is used:

- Every safe response sets a `csrf_token` HTTP-only cookie
- Unsafe requests (POST, PUT, DELETE, PATCH) must include the token in the `X-CSRF-Token` header
- CSRF check is bypassed for auth endpoints (`/api/v1/auth/*`), health check, and docs

---

## Data Encryption

### Encryption at Rest

- **Passwords:** bcrypt or PBKDF2-SHA256 with per-password random salt
- **User documents:** stored on disk with restricted file permissions
- **Database:** PostgreSQL data encryption at rest (filesystem-level)
- **Encryption key:** configured via `ENCRYPTION_KEY` env var; auto-generated with warning in production if unset

### Encryption in Transit

- **HTTPS/TLS** required in production
- TLS termination at the Nginx reverse proxy
- HSTS enabled in production (`max-age=31536000; includeSubDomains`)
- All API responses include `X-Content-Type-Options: nosniff`

---

## Secret Management

- All secrets are configured through **environment variables** — never in code
- The `.env` file is excluded from version control (in `.gitignore`)
- `JWT_SECRET` is auto-generated if not set (with a warning in production)
- `ENCRYPTION_KEY` is auto-generated if not set (with a warning in production)
- CI secrets are stored as GitHub Actions secrets, never in workflow files

---

## Audit Logging

All security-sensitive operations are logged to the `audit_logs` table:

| Event | Data Recorded |
|-------|---------------|
| User signup | Email, IP address, timestamp |
| User login | Email, IP address, session ID, timestamp |
| User logout | Email, session ID, timestamp |
| Token refresh | User, old session ID, new session ID |
| Refresh token reuse | User, reused token hash, IP, timestamp |
| Failed login | Email, IP address, attempt count, timestamp |
| Password change | User, timestamp |
| 2FA enable/disable | User, timestamp |
| Admin role change | Admin user, target user, new role, timestamp |
| Admin session revocation | Admin user, target session, timestamp |
| Account lockout | Email, IP, duration, timestamp |

Audit logs are retained for **90 days** with automatic daily cleanup.

---

## Security Headers Reference

Every HTTP response includes the following security headers:

| Header | Value | When |
|--------|-------|------|
| `X-Content-Type-Options` | `nosniff` | Always |
| `X-Frame-Options` | `DENY` | Always |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Always |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Always (configurable) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Production only |
| `Content-Security-Policy` | Configurable via `CSP_*` env vars | Always |
| `Cross-Origin-Embedder-Policy` | `require-corp` | Always (configurable) |
| `Cross-Origin-Opener-Policy` | `same-origin` | Always (configurable) |
| `Cross-Origin-Resource-Policy` | `same-origin` | Always (configurable) |
| `X-Request-ID` | UUID | Always |

---

## Vulnerable Dependency Scanning

- **CodeQL Analysis** runs on every push and pull request via `.github/workflows/codeql.yml`
- Scans both Python and JavaScript dependencies for known vulnerabilities
- Results appear as GitHub Security alerts
- Dependencies should be kept up to date; automated Dependabot alerts are enabled

---

## Reporting Vulnerabilities

If you discover a security vulnerability, please **do not** open a public GitHub issue. Instead, report it confidentially:

**Email:** security@nebula.dev

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Any potential impact
- Suggested fix (if applicable)

You can expect:

- **Acknowledgment** within 48 hours
- **Status update** within 5 business days
- **Fix timeline** communicated once triage is complete

We believe in coordinated disclosure. Please allow us reasonable time to address the issue before public discussion.

### Supported Versions

| Version | Supported |
|---------|-----------|
| 1.1.x (latest) | ✅ Security fixes |
| 1.0.x | ⚠️ Critical fixes only |
| < 1.0 | ❌ Not supported |
