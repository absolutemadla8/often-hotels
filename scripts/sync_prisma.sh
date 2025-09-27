#!/bin/bash

# Auto-sync Prisma schema with database changes
# This script watches for database changes and updates Prisma schema

echo "🔄 Starting Prisma Auto-Sync for Often Hotels..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Set environment variables
export DATABASE_URL=${DATABASE_URL:-"postgres://postgres:password@localhost:5433/often_hotels"}

# Function to sync schema
sync_schema() {
    echo -e "${BLUE}📊 Syncing Prisma schema with database...${NC}"
    
    # Pull latest schema from database
    npx prisma db pull --force
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Schema updated successfully${NC}"
        
        # Generate Prisma client
        npx prisma generate
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Prisma client generated${NC}"
        else
            echo -e "${RED}❌ Failed to generate Prisma client${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to sync schema${NC}"
    fi
}

# Function to check if database is accessible
check_database() {
    echo -e "${BLUE}🔍 Checking database connection...${NC}"
    
    # Try to connect to database
    npx prisma db pull --preview-feature > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database is accessible${NC}"
        return 0
    else
        echo -e "${RED}❌ Cannot connect to database${NC}"
        return 1
    fi
}

# Function to watch for changes
watch_changes() {
    echo -e "${YELLOW}👁️  Watching for database changes...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop watching${NC}"
    
    last_schema_hash=""
    
    while true; do
        if check_database; then
            # Get current schema hash
            current_schema_hash=$(npx prisma db pull --print | shasum | cut -d' ' -f1 2>/dev/null)
            
            if [ "$current_schema_hash" != "$last_schema_hash" ] && [ ! -z "$current_schema_hash" ]; then
                if [ ! -z "$last_schema_hash" ]; then
                    echo -e "${YELLOW}🔄 Database schema changed! Syncing...${NC}"
                    sync_schema
                else
                    echo -e "${BLUE}📊 Initial schema sync...${NC}"
                    sync_schema
                fi
                last_schema_hash="$current_schema_hash"
            fi
        else
            echo -e "${RED}⚠️  Database not accessible, retrying in 10 seconds...${NC}"
        fi
        
        sleep 10
    done
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping Prisma auto-sync...${NC}"
    echo -e "${GREEN}✅ Auto-sync stopped${NC}"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT

# Parse command line arguments
case "$1" in
    "sync")
        sync_schema
        ;;
    "watch")
        watch_changes
        ;;
    "studio")
        echo -e "${BLUE}🌟 Starting Prisma Studio...${NC}"
        npx prisma studio --port 5557
        ;;
    "init")
        echo -e "${BLUE}🚀 Initializing Prisma...${NC}"
        npm install
        sync_schema
        echo -e "${GREEN}✅ Prisma initialized${NC}"
        ;;
    *)
        echo -e "${BLUE}Prisma Auto-Sync Tool${NC}"
        echo ""
        echo "Usage: $0 {sync|watch|studio|init}"
        echo ""
        echo "Commands:"
        echo "  sync    - One-time schema sync with database"
        echo "  watch   - Continuously watch for database changes"
        echo "  studio  - Start Prisma Studio on port 5557"
        echo "  init    - Initialize Prisma (install deps + sync)"
        echo ""
        echo "Examples:"
        echo "  $0 init     # First time setup"
        echo "  $0 sync     # Sync schema once"
        echo "  $0 watch    # Auto-sync on changes"
        echo "  $0 studio   # Open Prisma Studio"
        ;;
esac