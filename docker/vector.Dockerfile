# Stage 1: Build stage
FROM python:3.11.9-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install core dependencies
RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt \
    numpy

# Install FAISS CPU only (for vector search)
RUN pip install --no-cache-dir --prefix=/install faiss-cpu

# Stage 2: Runtime
FROM python:3.11.9-slim-bookworm AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/nebula/.local/bin:$PATH" \
    VECTOR_INDEX_PATH=/app/storage/indexes \
    STORAGE_CACHE=/app/storage/cache

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with UID 1000
RUN groupadd -r nebula && useradd -r -u 1000 -g nebula -m -d /home/nebula -s /bin/sh nebula

# Copy installed dependencies from builder
COPY --from=builder /install /home/nebula/.local

# Copy application code
COPY --chown=nebula:nebula backend/app /app/app
COPY --chown=nebula:nebula backend/vector /app/vector
COPY --chown=nebula:nebula docker/vector-entrypoint.sh /app/vector-entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/storage /app/logs /tmp && \
    chmod 1777 /tmp && \
    chown -R nebula:nebula /app /tmp

# Switch to non-root user
USER nebula

# Expose port for metrics (optional)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health')" || exit 1

# Start vector worker
ENTRYPOINT ["dumb-init", "--"]
CMD ["/app/vector-entrypoint.sh", "worker"]
