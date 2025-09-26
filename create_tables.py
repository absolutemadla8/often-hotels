#!/usr/bin/env python3

import asyncio
from tortoise import Tortoise
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.config import settings

async def create_tables():
    # Initialize Tortoise ORM with same config as main.py
    # Use absolute path for SQLite database
    db_url = f"sqlite://{os.path.abspath('often_hotels.db')}"

    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["app.models.models", "aerich.models"],
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