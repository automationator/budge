#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Seed required data
echo "Seeding database..."
uv run python seed.py

# Start the application
exec "$@"
