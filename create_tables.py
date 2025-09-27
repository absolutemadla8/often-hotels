#!/usr/bin/env python3

import asyncio
from tortoise import Tortoise
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.config import settings

async def create_tables():
    # Initialize Tortoise ORM with PostgreSQL config
    db_url = settings.DATABASE_URL
    
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Handle PostgreSQL URL format for Tortoise ORM
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)

    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["app.models.models"],
                "default_connection": "default",
            },
        },
    }

    print(f"Connecting to database: {db_url}")
    await Tortoise.init(config=TORTOISE_ORM)

    print("Generating database schema...")
    await Tortoise.generate_schemas()

    print("Tables created successfully!")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(create_tables())