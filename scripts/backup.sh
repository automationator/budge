#!/bin/bash
# Budge Database Backup Script
#
# Creates a compressed PostgreSQL backup using pg_dump's custom format.
#
# Usage:
#   ./scripts/backup.sh                    # Creates timestamped backup
#   ./scripts/backup.sh my_backup          # Creates backup with custom name
#
# Environment variables:
#   COMPOSE_FILE    - Docker compose file (default: docker-compose.prod.yml)
#   BACKUP_DIR      - Directory to store backups (default: ./backups)
#   RETENTION_DAYS  - Days to keep old backups (default: 30)

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
BACKUP_NAME="${1:-budge_backup_$(date +%Y%m%d_%H%M%S)}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Load environment variables if .env.prod exists
if [[ -f "$PROJECT_DIR/.env.prod" ]]; then
    set -a
    source "$PROJECT_DIR/.env.prod"
    set +a
fi

POSTGRES_USER="${POSTGRES_USER:-budge}"
POSTGRES_DB="${POSTGRES_DB:-budge}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "Starting backup: $BACKUP_NAME"
echo "  Database: $POSTGRES_DB"
echo "  User: $POSTGRES_USER"

# Run pg_dump inside the database container
docker compose -f "$PROJECT_DIR/$COMPOSE_FILE" --env-file "$PROJECT_DIR/.env.prod" exec -T db \
    pg_dump -U "$POSTGRES_USER" \
    --schema=public \
    --format=custom \
    --verbose \
    "$POSTGRES_DB" > "$BACKUP_DIR/${BACKUP_NAME}.dump"

# Compress the backup
gzip -f "$BACKUP_DIR/${BACKUP_NAME}.dump"

# Calculate size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.dump.gz" | cut -f1)
echo ""
echo "Backup created: $BACKUP_DIR/${BACKUP_NAME}.dump.gz"
echo "Backup size: $BACKUP_SIZE"

# Clean up old backups
if [[ "$RETENTION_DAYS" -gt 0 ]]; then
    echo ""
    echo "Cleaning up backups older than $RETENTION_DAYS days..."
    DELETED=$(find "$BACKUP_DIR" -name "budge_backup_*.dump.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    if [[ "$DELETED" -gt 0 ]]; then
        echo "Deleted $DELETED old backup(s)"
    else
        echo "No old backups to delete"
    fi
fi

echo ""
echo "Backup complete!"
