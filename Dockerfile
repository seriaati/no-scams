# Multi-stage Docker build for no-scams Discord bot
# Optimized for production use with minimal image size

# Stage 1: Builder - Install dependencies and build the application
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Configure uv for optimal Docker builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy application code and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: Runtime - Minimal final image without uv
FROM python:3.12-slim-bookworm

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --system --gid 999 botuser \
    && useradd --system --gid 999 --uid 999 --create-home botuser

# Copy virtual environment from builder
COPY --from=builder --chown=botuser:botuser /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=botuser:botuser /app/run.py /app/run.py
COPY --from=builder --chown=botuser:botuser /app/no_scams /app/no_scams

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER botuser
WORKDIR /app

# Expose health check port
EXPOSE 8080

# Health check - polls the /health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the bot with optimizations (-OO removes docstrings and assertions)
CMD ["python", "-OO", "run.py"]
