# Self-Hosting Budge

This guide covers everything you need to know to run Budge on your own server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration Reference](#configuration-reference)
- [Operations](#operations)
- [Backups & Recovery](#backups--recovery)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Prerequisites

- **Docker** 20.10 or later
- **Docker Compose** v2.0 or later (included with Docker Desktop)
- **2GB RAM** minimum (4GB recommended)
- **1GB disk space** for the application, plus space for your data

### Verify Docker Installation

```bash
docker --version
docker compose version
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/budge.git
cd budge
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.prod.example .env.prod

# Generate secure secrets
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env.prod.tmp
echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)" >> .env.prod.tmp

# Edit .env.prod and replace the placeholder values with the generated ones
# Or manually edit .env.prod with your favorite editor
```

At minimum, you must set:
- `JWT_SECRET_KEY` - A random string of at least 32 characters
- `POSTGRES_PASSWORD` - A strong password for the database

### 3. Start Budge

```bash
make prod-up
```

This will:
1. Build the Docker images
2. Start all services (nginx, api, database)
3. Run database migrations

### 4. Access Budge

Open your browser to `http://localhost` (or your server's IP address).

Create your first account by clicking "Register".

## Configuration Reference

All configuration is done via environment variables in `.env.prod`.

### Required Settings

| Variable | Description |
|----------|-------------|
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens. Generate with `openssl rand -base64 32`. Must be at least 32 characters. |
| `POSTGRES_PASSWORD` | Password for the PostgreSQL database. Generate with `openssl rand -base64 24`. |

### Network Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HTTP_PORT` | `80` | Port to expose the application on |
| `CORS_ORIGINS` | `[]` | JSON array of allowed CORS origins. Example: `["https://budge.example.com"]` |
| `EXTRA_CORS_ORIGINS` | `[]` | Additional CORS origins (useful for Tailscale, etc.) |

### API Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `API_WORKERS` | `4` | Number of API workers. Recommended: 2-4 x CPU cores |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `budge` | Database username |
| `POSTGRES_DB` | `budge` | Database name |

## Operations

### Starting and Stopping

```bash
# Start Budge
make prod-up

# Stop Budge (preserves data)
make prod-down

# View logs
make prod-logs

# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f db
```

### Checking Health

```bash
# Check if all services are running
docker compose -f docker-compose.prod.yml ps

# Check nginx health
curl http://localhost/health

# Check API health
curl http://localhost/api/v1/health
```

### Resource Usage

```bash
# View resource usage
docker stats
```

Expected resource usage:
- **nginx**: ~10-20MB RAM
- **api**: ~100-300MB RAM (depends on worker count)
- **db**: ~100-200MB RAM (grows with data)

## Backups & Recovery

### Creating Backups

Budge uses PostgreSQL's `pg_dump` in custom format for backups. Backups are compressed with gzip.

```bash
# Create a backup
make prod-backup

# Backup is saved to ./backups/budge_backup_YYYYMMDD_HHMMSS.dump.gz
```

### Automated Backups

Add a cron job to create daily backups:

```bash
# Edit crontab
crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * cd /path/to/budge && ./scripts/backup.sh >> /var/log/budge-backup.log 2>&1
```

### Backup Retention

By default, backups older than 30 days are automatically deleted when a new backup is created. Change this with the `RETENTION_DAYS` environment variable:

```bash
RETENTION_DAYS=90 ./scripts/backup.sh
```

### Restoring from Backup

**Warning**: Restoring will delete all current data!

```bash
# List available backups
ls -la ./backups/

# Restore from a backup
./scripts/restore.sh ./backups/budge_backup_20240115_120000.dump.gz
```

The restore script will:
1. Stop the API service
2. Drop and recreate the database
3. Restore data from the backup
4. Start the API service

### Backup Best Practices

1. **Test your backups** - Periodically restore to a test environment
2. **Store backups offsite** - Copy backups to cloud storage or another server
3. **Monitor backup size** - Sudden changes may indicate issues
4. **Keep multiple backups** - Don't rely on a single backup

## Upgrading

### Standard Upgrade

```bash
# Stop the application
make prod-down

# Pull the latest code
git pull

# Rebuild and start
make prod-up
```

The `make prod-up` command automatically runs database migrations.

### Major Version Upgrades

For major version upgrades, check the release notes for any breaking changes or special migration steps.

```bash
# 1. Create a backup before upgrading
make prod-backup

# 2. Stop the application
make prod-down

# 3. Pull the new version
git fetch --tags
git checkout v2.0.0  # Replace with the version

# 4. Review any configuration changes
diff .env.prod .env.prod.example

# 5. Rebuild and start
make prod-up

# 6. Verify the application works
curl http://localhost/health
```

### Rolling Back

If an upgrade fails:

```bash
# 1. Stop the application
make prod-down

# 2. Checkout the previous version
git checkout v1.x.x

# 3. Restore from backup
./scripts/restore.sh ./backups/budge_backup_YYYYMMDD_HHMMSS.dump.gz

# 4. Rebuild and start
make prod-up
```

## Troubleshooting

### Application Won't Start

**Check logs:**
```bash
docker compose -f docker-compose.prod.yml logs
```

**Common issues:**

1. **"JWT_SECRET_KEY is required"**
   - Ensure `JWT_SECRET_KEY` is set in `.env.prod`
   - The key must be at least 32 characters

2. **"POSTGRES_PASSWORD is required"**
   - Ensure `POSTGRES_PASSWORD` is set in `.env.prod`

3. **Port already in use**
   - Change `HTTP_PORT` in `.env.prod`
   - Or stop the conflicting service

### Database Connection Issues

**Check if database is healthy:**
```bash
docker compose -f docker-compose.prod.yml exec db pg_isready
```

**Check database logs:**
```bash
docker compose -f docker-compose.prod.yml logs db
```

**Restart the database:**
```bash
docker compose -f docker-compose.prod.yml restart db
```

### API Errors

**Check API logs:**
```bash
docker compose -f docker-compose.prod.yml logs api
```

**Enable debug logging:**
Add `LOG_LEVEL=DEBUG` to `.env.prod` and restart:
```bash
make prod-down && make prod-up
```

### Permission Issues

If you see permission errors:

```bash
# Fix ownership of data directory
sudo chown -R 1000:1000 ./backups
```

### Clearing Everything and Starting Fresh

**Warning**: This deletes all data!

```bash
# Stop and remove everything including volumes
docker compose -f docker-compose.prod.yml down -v

# Rebuild and start fresh
make prod-up
```

## Advanced Configuration

### Running Behind a Reverse Proxy

If you're running Budge behind another reverse proxy (nginx, Traefik, Caddy), you may need to adjust the configuration.

**With Traefik:**

```yaml
# docker-compose.override.yml
services:
  nginx:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.budge.rule=Host(`budge.example.com`)"
      - "traefik.http.routers.budge.entrypoints=websecure"
      - "traefik.http.routers.budge.tls.certresolver=letsencrypt"
    ports: []  # Remove direct port exposure
```

**With Caddy:**

```
# Caddyfile
budge.example.com {
    reverse_proxy localhost:8080
}
```

Then set `HTTP_PORT=8080` in `.env.prod`.

### Adding SSL/TLS

For SSL, we recommend using a reverse proxy like Caddy or Traefik that handles certificates automatically. Alternatively:

1. **Tailscale** - Provides automatic HTTPS for your Tailscale domain
2. **Cloudflare Tunnel** - Free tunnels with automatic SSL

### Using an External Database

To use an external PostgreSQL database instead of the included one:

1. Remove or comment out the `db` service in a docker-compose override
2. Set these environment variables:
   ```bash
   POSTGRES_HOST=your-database-host.com
   POSTGRES_PORT=5432
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB=budge
   ```

### Customizing Worker Count

The number of API workers affects performance and memory usage:

```bash
# For a small server (1-2 CPU, 2GB RAM)
API_WORKERS=2

# For a medium server (4 CPU, 4GB RAM)
API_WORKERS=4

# For a large server (8+ CPU, 8GB+ RAM)
API_WORKERS=8
```

Rule of thumb: 2 x number of CPU cores, but monitor memory usage.

### Exposing Metrics

For monitoring with Prometheus, the API exposes a health endpoint:

```bash
curl http://localhost/api/v1/health
# Returns: {"status": "healthy"}
```

### Data Directory

All persistent data is stored in Docker volumes:

- `budge_postgres_data` - Database files

To find the volume location:
```bash
docker volume inspect budge_postgres_data
```
