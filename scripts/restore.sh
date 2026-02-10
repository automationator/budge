#!/bin/bash
# Budge Database Restore Script
#
# Restores a PostgreSQL backup created by backup.sh
#
# WARNING: This will DROP and recreate the database!
#
# Usage:
#   ./scripts/restore.sh ./backups/budge_backup_20240115_120000.dump.gz
#
# Environment variables:
#   COMPOSE_FILE - Docker compose file (default: docker-compose.prod.yml)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

# Check arguments
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 ./backups/budge_backup_20240115_120000.dump.gz"
    echo ""
    echo "Available backups:"
    if [[ -d "$PROJECT_DIR/backups" ]]; then
        ls -la "$PROJECT_DIR/backups"/*.dump.gz 2>/dev/null || echo "  No backups found"
    else
        echo "  No backups directory found"
    fi
    exit 1
fi

BACKUP_FILE="$1"

# Convert to absolute path if relative
if [[ ! "$BACKUP_FILE" = /* ]]; then
    BACKUP_FILE="$PROJECT_DIR/$BACKUP_FILE"
fi

# Verify backup file exists
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables if .env.prod exists
if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
    set -a
    source "$PROJECT_DIR/.env.prod"
    set +a
fi

POSTGRES_USER="${POSTGRES_USER:-budge}"
POSTGRES_DB="${POSTGRES_DB:-budge}"

echo "=========================================="
echo "         DATABASE RESTORE"
echo "=========================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Database:    $POSTGRES_DB"
echo "User:        $POSTGRES_USER"
echo ""
echo "WARNING: This will DROP the database '$POSTGRES_DB'"
echo "         and restore from the backup file."
echo "         All current data will be LOST!"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to confirm: " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo ""
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Step 1/4: Stopping API service..."
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" stop api || true

echo ""
echo "Step 2/4: Dropping and recreating database..."
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" \
    > /dev/null 2>&1 || true

docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"

docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
    psql -U "$POSTGRES_USER" -d postgres \
    -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"

echo ""
echo "Step 3/4: Restoring from backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
        pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --verbose --no-owner --no-privileges
else
    docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
        pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --verbose --no-owner --no-privileges < "$BACKUP_FILE"
fi

echo ""
echo "Step 4/4: Starting API service..."
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" start api

echo ""
echo "=========================================="
echo "         RESTORE COMPLETE"
echo "=========================================="
echo ""
echo "The database has been restored from:"
echo "  $BACKUP_FILE"
echo ""
echo "You may want to verify the application is working correctly."
