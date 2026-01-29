# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install system dependencies required for building Python packages
# libpq-dev is needed for building psycopg (psycopg3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution and installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy requirements file
COPY backend/requirements.txt .

# Create virtual environment and install dependencies
# We use --system to install into the system python in the builder,
# or create a venv. Venv is cleaner for multi-stage copy.
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
RUN uv pip install --no-cache -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install runtime system dependencies
# libpq5 is required for PostgreSQL connection
# curl is used for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
# Assuming build context is project root
COPY backend/src ./src
COPY backend/alembic ./alembic
COPY backend/alembic.ini .
COPY backend/scripts ./scripts

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Switch to non-root user
USER appuser

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/monitoring/health || exit 1

# Expose the application port
EXPOSE 8000

# Run the application using uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
