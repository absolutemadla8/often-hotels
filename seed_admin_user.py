#!/usr/bin/env python3
"""
Seed admin user with trippy credentials

Creates an admin user for testing and management purposes.
"""
import asyncio
import secrets
import string
from tortoise import Tortoise
from app.core.config import settings
from app.models.models import User
from app.core.security import get_password_hash

async def seed_admin_user():
    """Create admin user with trippy credentials"""
    print("🔧 Seeding admin user...")
    
    # Get database URL from settings
    db_url = settings.DATABASE_URL
    
    if db_url and db_url.startswith('postgresql://'):
        # Convert PostgreSQL URL format for Tortoise ORM
        db_url = db_url.replace('postgresql://', 'postgres://', 1)
        # Handle SSL mode parameter for Tortoise ORM
        if 'sslmode=require' in db_url:
            db_url = db_url.replace('?sslmode=require', '').replace('&sslmode=require', '')
    
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
        
        # Generate a random secure password
        def generate_password(length=12):
            """Generate a secure random password"""
            alphabet = string.ascii_letters + string.digits + "!@#$%&*"
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            return password
        
        # Admin user credentials
        admin_email = "trippy@oftenhotels.com"
        admin_password = "TrIpPy2025!"  # Simple secure password
        admin_full_name = "Trippy Admin"
        
        # Check if admin user already exists
        existing_admin = await User.get_or_none(email=admin_email)
        if existing_admin:
            print(f"⚠️ Admin user already exists with email: {admin_email}")
            print(f"   User ID: {existing_admin.id}")
            print(f"   Full Name: {existing_admin.full_name}")
            print(f"   Is Active: {existing_admin.is_active}")
            print(f"   Is Superuser: {existing_admin.is_superuser}")
            
            # Update password and ensure superuser status
            existing_admin.hashed_password = get_password_hash(admin_password)
            existing_admin.is_superuser = True
            existing_admin.is_active = True
            existing_admin.full_name = admin_full_name
            await existing_admin.save()
            
            print("✅ Updated existing admin user with new password")
        else:
            # Create new admin user
            admin_user = await User.create(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                full_name=admin_full_name,
                is_active=True,
                is_superuser=True
            )
            print("✅ Created new admin user")
            print(f"   User ID: {admin_user.id}")
        
        # Admin credentials output
        print("\n🎉 Admin User Seeded Successfully!")
        print("=" * 50)
        print("📧 Admin Credentials:")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Full Name: {admin_full_name}")
        print("=" * 50)
        
        # Authentication routes information
        print("\n🔐 Authentication Routes:")
        print("   POST /api/v1/auth/login")
        print("     - Login with email and password")
        print("     - Returns access_token and refresh_token")
        print()
        print("   GET /api/v1/auth/me")
        print("     - Get current user information")
        print("     - Requires Authorization header")
        print()
        print("   POST /api/v1/auth/refresh")
        print("     - Refresh access token")
        print("     - Use refresh_token from login response")
        print()
        
        # Admin endpoints information
        print("🛡️ Admin Hotel Tracking Endpoints:")
        print("   POST /api/v1/admin/hotel-tracking/start")
        print("     - Start hotel tracking task")
        print("     - Requires admin authentication")
        print()
        print("   GET /api/v1/admin/hotel-tracking/status")
        print("     - Get tracking task status")
        print("     - Requires admin authentication")
        print()
        print("   POST /api/v1/admin/hotel-tracking/stop")
        print("     - Stop running tracking tasks")
        print("     - Requires admin authentication")
        print()
        
        # Login example
        print("💡 Login Example (curl):")
        print(f"""curl -X POST "http://localhost:8000/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{{"email": "{admin_email}", "password": "{admin_password}"}}'""")
        print()
        
        print("💡 Use Admin Token Example:")
        print("""curl -X POST "http://localhost:8000/api/v1/admin/hotel-tracking/start" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \\
  -H "Content-Type: application/json" """)
        print()
        
        # Security note
        print("🚨 Security Note:")
        print("   - Keep these credentials secure")
        print("   - Change password after first login in production")
        print("   - Admin user has full system access")
        print()
        
    except Exception as e:
        print(f"❌ Error seeding admin user: {e}")
        raise
    finally:
        await Tortoise.close_connections()
        print("🔌 Database connections closed")

if __name__ == "__main__":
    asyncio.run(seed_admin_user())