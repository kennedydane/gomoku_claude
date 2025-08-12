# Multi-stage Dockerfile for FastAPI backend with uv
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies with minimal packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv
RUN pip install --no-cache-dir uv

# Create non-root user early
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/sh appuser

# Set working directory
WORKDIR /app

# Copy dependency files (as appuser for better security)
COPY --chown=appuser:appuser pyproject.toml README.md ./

# Create virtual environment and install base dependencies
RUN uv sync --frozen --no-dev && rm -rf /tmp/uv-cache

# Copy source code
COPY --chown=appuser:appuser src/ ./src/

# Create logs directory
RUN mkdir -p /app/logs /app/static && chown -R appuser:appuser /app

# Development stage
FROM base as development
USER root
# Install development dependencies
RUN uv sync --frozen && rm -rf /tmp/uv-cache
USER appuser
# Command for development (with hot reload)
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage  
FROM base as production

# Switch to non-root user
USER appuser

# Health check using internal health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Use more robust production settings
CMD ["uv", "run", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-log", \
     "--log-level", "info"]