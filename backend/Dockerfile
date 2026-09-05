# ──────────────────────────────────────────────────────────────────────
# CodeIntel Backend — Production Dockerfile
# Multi-stage build for a lean production image
# ──────────────────────────────────────────────────────────────────────

# Stage 1: Builder — install dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install dependencies into a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ──────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — lean image with only what's needed
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r codeintel && \
    useradd -r -g codeintel -d /app -s /sbin/nologin codeintel

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Run as non-root user
USER codeintel

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
