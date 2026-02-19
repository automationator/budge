FROM python:3.14-slim

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies using locked versions
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY backend/src/ ./src/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./
COPY backend/seed.py ./

# Install the project itself
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Copy entrypoint
COPY backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# Run as non-root user
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --ingroup appuser appuser
RUN chown -R appuser:appuser /app
ENV UV_CACHE_DIR=/app/.cache/uv
USER appuser

ENTRYPOINT ["./entrypoint.sh"]

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
