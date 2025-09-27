#!/usr/bin/env python3

import asyncio
from tortoise import Tortoise
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.models import User
from app.core.security import get_password_hash

async def create_default_user():
    # Initialize Tortoise ORM with PostgreSQL config
    from app.core.config import settings
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

    # Check if default user exists
    existing_user = await User.get_or_none(email="test@example.com")
    if existing_user:
        print("Default user already exists")
        user = existing_user
    else:
        # Create default user
        print("Creating default user...")
        user = await User.create(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        print(f"Created user with ID: {user.id}")

    await Tortoise.close_connections()
    return user.id

if __name__ == "__main__":
    user_id = asyncio.run(create_default_user())
    print(f"Default user ID: {user_id}")