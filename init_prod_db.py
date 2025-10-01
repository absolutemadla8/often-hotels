#!/usr/bin/env python3
"""
Initialize production database with schema and tables
"""
import asyncio
import os
from tortoise import Tortoise
from app.core.config import settings

async def init_database():
    """Initialize database schema"""
    print("🔧 Initializing production database schema...")
    
    # Get database URL from settings
    db_url = settings.DATABASE_URL
    
    if db_url and db_url.startswith('postgresql://'):
        # Convert PostgreSQL URL format for Tortoise ORM
        db_url = db_url.replace('postgresql://', 'postgres://', 1)
        # Handle SSL mode parameter for Tortoise ORM
        if 'sslmode=require' in db_url:
            db_url = db_url.replace('?sslmode=require', '').replace('&sslmode=require', '')
    
    print(f"📊 Database URL: {db_url}")
    
    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["app.models.models"],
                "default_connection": "default",
            },
        },
    }
    
    try:
        # Initialize Tortoise ORM
        await Tortoise.init(config=TORTOISE_ORM)
        print("✅ Connected to database")
        
        # Generate schemas (create tables)
        await Tortoise.generate_schemas()
        print("✅ Database schema created successfully!")
        
        # List created tables
        conn = Tortoise.get_connection("default")
        tables = await conn.execute_query("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
        print(f"📋 Created tables: {[table['tablename'] for table in tables[1]]}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        raise
    finally:
        await Tortoise.close_connections()
        print("🔌 Database connections closed")

if __name__ == "__main__":
    asyncio.run(init_database())