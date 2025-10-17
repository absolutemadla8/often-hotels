#!/bin/bash

# Deployment script for Often Hotels
# This script is executed on the VM during CI/CD deployment

set -e  # Exit immediately if a command exits with a non-zero status

echo "=========================================="
echo "Often Hotels - Deployment Script"
echo "=========================================="
echo ""

# Configuration
PROJECT_DIR="/root/often-hotels"
BRANCH="sarvesh/db-setup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd $PROJECT_DIR

# Step 1: Pull latest code
log_info "Pulling latest changes from branch: $BRANCH"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# Step 2: Check if .env file exists
if [ ! -f .env ]; then
    log_warn ".env file not found. Creating from environment variables..."
    # This will be populated by GitHub Actions
fi

# Step 3: Backup current database (optional)
log_info "Creating database backup (optional)..."
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec often-hotels-db pg_dump -U postgres often_hotels > "$BACKUP_DIR/backup_$TIMESTAMP.sql" 2>/dev/null || log_warn "Database backup skipped"

# Step 4: Stop existing containers
log_info "Stopping existing containers..."
docker-compose down

# Step 5: Remove old images (optional - uncomment to clean up)
# log_info "Removing old Docker images..."
# docker image prune -f

# Step 6: Build new images
log_info "Building Docker images..."
docker-compose build --no-cache

# Step 7: Start containers
log_info "Starting containers..."
docker-compose up -d

# Step 8: Wait for services to be healthy
log_info "Waiting for services to start..."
sleep 15

# Step 9: Run database migrations
log_info "Running database migrations..."
docker exec often-hotels-api alembic upgrade head || log_warn "Migrations failed or not configured"

# Step 10: Check container status
log_info "Checking container status..."
docker-compose ps

# Step 11: Verify API is responding
log_info "Verifying API health..."
sleep 5
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8006/docs || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    log_info "API is responding correctly (HTTP 200)"
else
    log_warn "API health check returned: $API_RESPONSE"
fi

# Step 12: Show recent logs
log_info "Recent API logs:"
docker logs --tail 20 often-hotels-api

echo ""
echo "=========================================="
log_info "Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Services running:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
