#!/bin/bash

# Start Celery services for development
echo "🚀 Starting Celery services for Often Hotels..."

# Set environment variables if not already set
export DATABASE_URL=${DATABASE_URL:-"postgres://postgres:password@localhost:5433/often_hotels"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6380/0"}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Starting Celery Worker...${NC}"
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=4 &
WORKER_PID=$!

echo -e "${BLUE}⏰ Starting Celery Beat Scheduler...${NC}"
celery -A app.core.celery_app:celery_app beat --loglevel=info &
BEAT_PID=$!

echo -e "${BLUE}🌸 Starting Celery Flower Monitoring...${NC}"
celery -A app.core.celery_app:celery_app flower --port=5555 &
FLOWER_PID=$!

echo -e "${GREEN}✅ All Celery services started!${NC}"
echo -e "${YELLOW}📊 Flower monitoring: http://localhost:5555${NC}"
echo -e "${YELLOW}🔧 Worker PID: $WORKER_PID${NC}"
echo -e "${YELLOW}📅 Beat PID: $BEAT_PID${NC}"
echo -e "${YELLOW}🌸 Flower PID: $FLOWER_PID${NC}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping Celery services...${NC}"
    kill $WORKER_PID $BEAT_PID $FLOWER_PID 2>/dev/null
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT

# Wait for all background processes
wait