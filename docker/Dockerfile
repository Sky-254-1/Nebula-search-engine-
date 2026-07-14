FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

RUN addgroup --system nebula && adduser --system --ingroup nebula nebula

COPY --from=builder /root/.local /root/.local

COPY backend/app /app/app
COPY backend/vector /app/vector
COPY docker/scheduler-entrypoint.sh /app/scheduler-entrypoint.sh

RUN mkdir -p /app/storage && chown -R nebula:nebula /app /app/scheduler-entrypoint.sh && chmod +x /app/scheduler-entrypoint.sh

USER nebula

EXPOSE 8000/tcp

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
