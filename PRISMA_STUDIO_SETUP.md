# Prisma Studio Integration Guide

This document explains how Prisma Studio is integrated alongside Tortoise ORM for database visualization and auto-schema detection.

## 🎯 **Important: Dual ORM Setup**

**⚠️ This is NOT a replacement for Tortoise ORM!**

- **Tortoise ORM** = Source of truth for Python application
- **Prisma Studio** = Database visualization and management GUI
- **Auto-sync** = Prisma schema automatically updates when database changes

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Tortoise ORM   │───▶│   PostgreSQL    │◀───│ Prisma Studio   │
│                 │    │                 │    │                 │
│ • Models        │    │ • Tables        │    │ • Visualization │
│ • Migrations    │    │ • Data          │    │ • Data Editing  │
│ • Source Truth  │    │ • Schema        │    │ • Schema View   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   Auto-Sync     │
                        │                 │
                        │ • Watch Changes │
                        │ • Update Schema │
                        │ • No Conflicts  │
                        └─────────────────┘
```

## 🚀 Quick Start

### **1. Initialize Prisma (First Time)**
```bash
# Install dependencies and sync schema
./scripts/sync_prisma.sh init
```

### **2. Start Services**
```bash
# With Docker (includes Prisma Studio)
docker-compose up -d

# Or manually
./scripts/sync_prisma.sh studio
```

### **3. Access Interfaces**
- **Prisma Studio**: http://localhost:5557
- **Flower (Celery)**: http://localhost:5555
- **FastAPI**: http://localhost:8000

## 📊 **Port Allocation**

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| FastAPI | 8000 | http://localhost:8000 | Main application |
| PostgreSQL | 5433 | localhost:5433 | Database |
| Redis | 6380 | localhost:6380 | Task queue |
| **Flower** | **5555** | http://localhost:5555 | **Celery monitoring** |
| **Prisma Studio** | **5557** | http://localhost:5557 | **Database GUI** |

**No port conflicts!** Flower (5555) and Prisma Studio (5557) run on different ports.

## 🔄 Auto-Schema Detection & Updates

### **How Auto-Sync Works:**

1. **Database Changes** (via Tortoise ORM migrations)
2. **Auto-Detection** (script watches database schema)
3. **Schema Update** (Prisma schema.prisma auto-updates)
4. **Client Generation** (Prisma client regenerates)
5. **Studio Refresh** (UI reflects new schema)

### **Auto-Sync Commands:**

```bash
# One-time sync
./scripts/sync_prisma.sh sync

# Continuous watching (auto-sync on changes)
./scripts/sync_prisma.sh watch

# Start Prisma Studio
./scripts/sync_prisma.sh studio

# Full initialization
./scripts/sync_prisma.sh init
```

### **What Triggers Auto-Sync:**

✅ **Automatically Detected:**
- New tables created by Tortoise migrations
- Column additions/removals
- Data type changes
- Index modifications
- Relationship changes

✅ **Manual Sync Available:**
- Run `./scripts/sync_prisma.sh sync` anytime
- Docker service auto-syncs on startup

## 🛠️ **Development Workflow**

### **Typical Development Flow:**

1. **Make Model Changes** (in Tortoise ORM)
   ```python
   # app/models/models.py
   class NewModel(Model):
       name = fields.CharField(max_length=100)
       created_at = fields.DatetimeField(auto_now_add=True)
   ```

2. **Create Migration** (Tortoise/Alembic)
   ```bash
   # Generate migration
   alembic revision --autogenerate -m "add new model"
   
   # Apply migration
   alembic upgrade head
   ```

3. **Auto-Sync Happens** (Prisma detects changes)
   - If watching: Immediate sync
   - If not watching: Manual sync

4. **View in Prisma Studio** (Updated schema visible)
   - Refresh browser
   - New tables/columns appear
   - Data is editable

### **Manual Sync When Needed:**

```bash
# After database changes
./scripts/sync_prisma.sh sync

# Start continuous monitoring
./scripts/sync_prisma.sh watch &
```

## 📱 **Prisma Studio Features**

### **What You Can Do:**

✅ **Data Browsing:**
- View all tables and relationships
- Browse data with pagination
- Filter and search records
- View related data

✅ **Data Editing:**
- Add new records
- Edit existing records
- Delete records
- Handle relationships

✅ **Schema Visualization:**
- See table structures
- View relationships
- Understand data types
- Navigate foreign keys

✅ **Querying:**
- Simple queries via UI
- Export data
- Import data

### **What You CANNOT Do:**

❌ **Schema Changes** (Prisma Studio is read-only for schema)
❌ **Migrations** (Use Tortoise/Alembic)
❌ **Production Writes** (Use with caution)

## 🔧 **Configuration Details**

### **Prisma Schema (`prisma/schema.prisma`)**

The schema file is **auto-generated** and mirrors your Tortoise models:

```prisma
// Auto-generated - DO NOT EDIT MANUALLY
model User {
  id              Int      @id @default(autoincrement())
  email           String   @unique @db.VarChar(255)
  hashed_password String   @db.VarChar(255)
  is_active       Boolean  @default(true)
  created_at      DateTime @default(now()) @db.Timestamptz(6)
  updated_at      DateTime @updatedAt @db.Timestamptz(6)

  // Auto-detected relationships
  tasks           Task[]
  refresh_tokens  RefreshToken[]

  @@map("users")
}
```

### **Docker Configuration**

```yaml
# docker-compose.yml
prisma-studio:
  image: node:18-alpine
  container_name: often-hotels-prisma-studio
  command: sh -c "npm install && npx prisma db pull && npx prisma studio --port 5557 --hostname 0.0.0.0"
  ports:
    - "5557:5557"
  environment:
    - DATABASE_URL=postgres://postgres:password@db:5432/often_hotels
  volumes:
    - ./prisma:/app/prisma
    - ./package.json:/app/package.json
    - prisma_node_modules:/app/node_modules
  depends_on:
    db:
      condition: service_healthy
```

### **Auto-Sync Script Features**

```bash
# scripts/sync_prisma.sh
./scripts/sync_prisma.sh watch   # Continuous monitoring
./scripts/sync_prisma.sh sync    # One-time sync
./scripts/sync_prisma.sh studio  # Start Prisma Studio
./scripts/sync_prisma.sh init    # First-time setup
```

**Monitoring Logic:**
- Checks database every 10 seconds
- Compares schema hashes
- Auto-syncs when changes detected
- Handles connection failures gracefully

## 🚨 **Important Considerations**

### **Development Environment**

✅ **Safe to Use:**
- Data browsing and visualization
- Quick data edits for testing
- Schema exploration
- Relationship understanding

### **Production Environment**

⚠️ **Use with Caution:**
- Read-only access recommended
- No direct data editing
- Schema viewing only
- Monitor-only mode

### **Data Consistency**

- **Source of Truth**: Tortoise ORM models
- **Schema Updates**: Via Tortoise migrations
- **Data Editing**: Prefer application APIs
- **Bulk Operations**: Use proper scripts

## 🐛 **Troubleshooting**

### **Common Issues:**

**1. Schema Out of Sync**
```bash
# Force sync
./scripts/sync_prisma.sh sync
```

**2. Prisma Studio Won't Start**
```bash
# Check database connection
docker-compose logs prisma-studio

# Restart service
docker-compose restart prisma-studio
```

**3. Port Conflicts**
```bash
# Check what's using ports
lsof -i :5555  # Flower
lsof -i :5557  # Prisma Studio
```

**4. Auto-Sync Not Working**
```bash
# Start manual watching
./scripts/sync_prisma.sh watch

# Check database accessibility
./scripts/sync_prisma.sh sync
```

### **Database Connection Issues**

**Local Development:**
```bash
# Check PostgreSQL is running
docker-compose ps db

# Test connection
psql -h localhost -p 5433 -U postgres -d often_hotels
```

**Environment Variables:**
```bash
# Verify DATABASE_URL
echo $DATABASE_URL

# For Prisma (if different)
export DATABASE_URL="postgres://postgres:password@localhost:5433/often_hotels"
```

## 🔐 **Security Notes**

### **Access Control:**
- Prisma Studio has **no built-in authentication**
- Use firewall rules in production
- Consider VPN access for production
- Monitor access logs

### **Database Permissions:**
- Prisma uses same DB user as application
- Can read and write all data
- Be careful with data modifications
- Use read-only replicas if available

## 📈 **Best Practices**

### **Development Workflow:**
1. Make changes in **Tortoise models**
2. Create **Alembic migrations**
3. Apply migrations to database
4. Let **auto-sync** update Prisma schema
5. Use **Prisma Studio** for data visualization

### **Data Management:**
1. **Browse data** in Prisma Studio
2. **Edit data** via application APIs (preferred)
3. **Quick fixes** via Prisma Studio (development only)
4. **Bulk operations** via custom scripts

### **Schema Changes:**
1. **Always** use Tortoise ORM for schema changes
2. **Never** edit `prisma/schema.prisma` manually
3. **Let auto-sync** handle schema updates
4. **Commit** generated schema files to git

## 🎉 **Benefits of This Setup**

✅ **Best of Both Worlds:**
- **Tortoise ORM**: Python-native, async, type-safe
- **Prisma Studio**: Beautiful GUI, easy data management

✅ **No Conflicts:**
- Different ports (5555 vs 5557)
- Separate concerns
- Auto-synchronization

✅ **Developer Experience:**
- Visual database browsing
- Quick data manipulation
- Schema understanding
- Relationship visualization

✅ **Production Ready:**
- Tortoise ORM handles production workload
- Prisma Studio for monitoring/debugging
- No performance impact
- Optional component

This setup gives you the best database development experience while maintaining the robustness of Tortoise ORM for your Python application!