#!/usr/bin/env python3
"""
Generate long-living JWT token for admin user

Creates a 6-month access token for the admin user.
"""
import asyncio
from datetime import datetime, timedelta
from tortoise import Tortoise
from app.core.config import settings
from app.core.security import create_access_token
from app.models.models import User

async def generate_long_token():
    """Generate 6-month JWT token for admin user"""
    print("🔧 Generating 6-month JWT token for admin...")
    
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
        
        # Get admin user
        admin_user = await User.get_or_none(email="trippy@oftenhotels.com")
        if not admin_user:
            print("❌ Admin user not found")
            return
        
        print(f"✅ Found admin user: {admin_user.email} (ID: {admin_user.id})")
        print(f"   Is superuser: {admin_user.is_superuser}")
        print(f"   Is active: {admin_user.is_active}")
        
        # Generate 6-month token (180 days)
        token_expires = timedelta(days=180)
        long_token = create_access_token(
            data={"sub": str(admin_user.id)}, 
            expires_delta=token_expires
        )
        
        # Calculate expiration date
        expiry_date = datetime.utcnow() + token_expires
        
        print("\n🎉 Long-living JWT Token Generated!")
        print("=" * 60)
        print("📧 Admin Credentials:")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: admin123")
        print(f"   User ID: {admin_user.id}")
        print()
        print("🔑 6-Month JWT Token:")
        print(f"   {long_token}")
        print()
        print(f"⏰ Token Details:")
        print(f"   Valid for: 180 days (6 months)")
        print(f"   Expires on: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Expires timestamp: {expiry_date.timestamp()}")
        print("=" * 60)
        
        print("\n💡 Usage Examples:")
        print()
        print("🔍 Test Authentication:")
        print(f"""curl -X GET "http://localhost:8000/api/v1/auth/me" \\
  -H "Authorization: Bearer {long_token}" """)
        print()
        
        print("🛡️ Start Hotel Tracking (Admin):")
        print(f"""curl -X POST "http://localhost:8000/api/v1/admin/hotel-tracking/start" \\
  -H "Authorization: Bearer {long_token}" \\
  -H "Content-Type: application/json" """)
        print()
        
        print("🔍 Enhanced Hotel Search:")
        print(f"""curl -X GET "http://localhost:8000/api/v1/hotels/search?destination_ids=1&start_date=2025-12-01&end_date=2025-12-05&search=luxury&page=1" \\
  -H "Authorization: Bearer {long_token}" """)
        print()
        
        print("📊 Get Hotel Details:")
        print(f"""curl -X GET "http://localhost:8000/api/v1/hotels/123" \\
  -H "Authorization: Bearer {long_token}" """)
        print()
        
        # Save to file for easy access
        token_info = {
            "admin_email": admin_user.email,
            "admin_password": "admin123",
            "user_id": admin_user.id,
            "access_token": long_token,
            "token_type": "bearer",
            "expires_in_days": 180,
            "expires_on": expiry_date.isoformat(),
            "expires_timestamp": expiry_date.timestamp(),
            "generated_on": datetime.utcnow().isoformat()
        }
        
        import json
        with open("admin_6month_token.json", "w") as f:
            json.dump(token_info, f, indent=2)
        
        print("💾 Token saved to: admin_6month_token.json")
        print()
        
        print("🚨 Security Notes:")
        print("   - This token is valid for 6 months")
        print("   - Store securely and do not share")
        print("   - Admin token has full system access")
        print("   - Use HTTPS in production")
        print("   - Consider token rotation for enhanced security")
        
    except Exception as e:
        print(f"❌ Error generating token: {e}")
        raise
    finally:
        await Tortoise.close_connections()
        print("\n🔌 Database connections closed")

if __name__ == "__main__":
    asyncio.run(generate_long_token())