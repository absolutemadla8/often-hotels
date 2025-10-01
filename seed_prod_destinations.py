#!/usr/bin/env python3
"""
Seed specific destinations and areas to production database to match current local structure
"""
import asyncio
from tortoise import Tortoise
from app.core.config import settings
from app.models.models import Country, Destination, Area

async def seed_destinations_and_areas():
    """Seed destinations and areas matching current local structure"""
    print("🏖️ Seeding destinations and areas to production database...")
    
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
        print("✅ Connected to production database")
        
        # Get country IDs
        indonesia = await Country.get(name="Indonesia")
        india = await Country.get(name="India")
        print(f"📍 Found Indonesia (ID: {indonesia.id}) and India (ID: {india.id})")
        
        # Create Bali destination
        bali, created = await Destination.get_or_create(
            name="Bali",
            defaults={
                "display_name": "Bali",
                "destination_type": "PROVINCE",
                "country_id": indonesia.id,
                "latitude": -8.4095,
                "longitude": 115.1889,
                "tourist_rating": 4.8,
                "is_popular": True,
                "is_active": True,
                "tracking": True,
                "numberofdaystotrack": 60,
                "description": "Bali is a province of Indonesia and the westernmost of the Lesser Sunda Islands. Located east of Java and west of Lombok, the province includes the island of Bali and a few smaller neighbouring islands, notably Nusa Penida, Nusa Lembongan, and Nusa Ceningan.",
                "famous_attractions": ["Ubud Rice Terraces", "Tanah Lot Temple", "Uluwatu Temple", "Sacred Monkey Forest", "Mount Batur"]
            }
        )
        print(f"🌴 {'Created' if created else 'Found'} Bali destination (ID: {bali.id})")
        
        # Create Gili Trawangan destination
        gili, created = await Destination.get_or_create(
            name="Gili Trawangan",
            defaults={
                "display_name": "Gili Trawangan",
                "destination_type": "ISLAND",
                "country_id": indonesia.id,
                "latitude": -8.3523,
                "longitude": 116.0325,
                "tourist_rating": 4.5,
                "is_popular": True,
                "is_active": True,
                "tracking": True,
                "numberofdaystotrack": 60,
                "description": "Gili Trawangan is the largest of the three small Gili Islands off the coast of Lombok, Indonesia. Known for its pristine beaches, crystal-clear waters, and vibrant nightlife.",
                "famous_attractions": ["Sunset Beach", "Night Market", "Turtle Point", "Shark Point", "Villa Ombak"]
            }
        )
        print(f"🏝️ {'Created' if created else 'Found'} Gili Trawangan destination (ID: {gili.id})")
        
        # Create Mumbai destination
        mumbai, created = await Destination.get_or_create(
            name="Mumbai",
            defaults={
                "display_name": "Mumbai",
                "destination_type": "CITY",
                "country_id": india.id,
                "latitude": 19.076,
                "longitude": 72.8777,
                "tourist_rating": 4.2,
                "is_popular": True,
                "is_active": True,
                "tracking": True,
                "numberofdaystotrack": 60,
                "description": "Mumbai is the capital city of the Indian state of Maharashtra and the de facto financial centre of India. The city is the most populous city in India, and the fourth most populous city in the world.",
                "famous_attractions": ["Gateway of India", "Marine Drive", "Elephanta Caves", "Juhu Beach", "Bollywood Studios"]
            }
        )
        print(f"🏙️ {'Created' if created else 'Found'} Mumbai destination (ID: {mumbai.id})")
        
        # Create Ubud area under Bali
        ubud, created = await Area.get_or_create(
            name="Ubud",
            destination_id=bali.id,
            defaults={
                "display_name": "Ubud, Bali",
                "area_type": "town",
                "country_id": indonesia.id,
                "latitude": -8.5069,
                "longitude": 115.2625,
                "description": "Cultural heart of Bali known for art, temples, yoga retreats, and rice terraces",
                "is_active": True,
                "is_popular": True,
                "tracking": True
            }
        )
        print(f"🎨 {'Created' if created else 'Found'} Ubud area under Bali (ID: {ubud.id})")
        
        # Create Nusa Dua area under Bali
        nusa_dua, created = await Area.get_or_create(
            name="Nusa Dua",
            destination_id=bali.id,
            defaults={
                "display_name": "Nusa Dua, Bali",
                "area_type": "resort_area",
                "country_id": indonesia.id,
                "latitude": -8.8017,
                "longitude": 115.2289,
                "description": "Nusa Dua is an upscale resort area on the southern peninsula of Bali, Indonesia. Known for its luxurious hotels, pristine beaches, world-class golf courses, and the Bali Collection shopping center.",
                "is_active": True,
                "is_popular": True,
                "tracking": True
            }
        )
        print(f"🏖️ {'Created' if created else 'Found'} Nusa Dua area under Bali (ID: {nusa_dua.id})")
        
        # Verify seeded data
        total_destinations = await Destination.filter(tracking=True).count()
        total_areas = await Area.filter(tracking=True).count()
        
        print(f"\n✅ Seeding completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Tracking destinations: {total_destinations}")
        print(f"   - Tracking areas: {total_areas}")
        
        # List all tracking destinations and areas
        print(f"\n📋 Current tracking setup:")
        tracking_destinations = await Destination.filter(tracking=True).prefetch_related('country')
        for dest in tracking_destinations:
            print(f"   🎯 {dest.name} ({dest.destination_type}) - {dest.country.name} - {dest.numberofdaystotrack} days")
        
        tracking_areas = await Area.filter(tracking=True).prefetch_related('destination', 'country')
        for area in tracking_areas:
            print(f"   📍 {area.name} → {area.destination.name} ({area.country.name})")
        
    except Exception as e:
        print(f"❌ Error seeding destinations: {e}")
        raise
    finally:
        await Tortoise.close_connections()
        print("🔌 Database connections closed")

if __name__ == "__main__":
    asyncio.run(seed_destinations_and_areas())