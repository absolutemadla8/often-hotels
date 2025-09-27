#!/usr/bin/env python3

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tortoise import Tortoise
from core.config import settings
from models.models import Country, Destination

# Comprehensive destination data for Indonesian destinations
DESTINATIONS_DATA = [
    {
        "name": "Ubud",
        "display_name": "Ubud, Bali",
        "local_name": "Ubud",
        "destination_type": "town",
        "state_province": "Bali",
        "administrative_area": "Gianyar Regency",
        "latitude": -8.5069,
        "longitude": 115.2625,
        "description": "Ubud is a town on the Indonesian island of Bali in Ubud District, located amongst rice paddies and steep ravines in the central foothills of the Gianyar regency. Known as the cultural heart of Bali, Ubud is famous for its traditional crafts and dance, yoga retreats, and stunning natural beauty.",
        "population": 74320,
        "area_km2": 32.0,
        "elevation_m": 200,
        "tourist_rating": 4.6,
        "best_visit_months": [4, 5, 6, 7, 8, 9, 10],
        "climate_type": "Tropical monsoon",
        "famous_attractions": [
            "Sacred Monkey Forest Sanctuary",
            "Tegallalang Rice Terraces", 
            "Ubud Palace",
            "Campuhan Ridge Walk",
            "Saraswati Temple",
            "Ubud Traditional Art Market",
            "Goa Gajah (Elephant Cave)",
            "Museum Puri Lukisan"
        ],
        "timezone": "Asia/Makassar",
        "airport_codes": ["DPS"],
        "common_languages": ["Indonesian", "Balinese"],
        "external_ids": {
            "wikidata": "Q1020776",
            "geonames": "1621177"
        },
        "google_place_id": "ChIJzWXFYYs0wS0RMIANHJw3ZAQ",
        "is_active": True,
        "is_popular": True,
        "is_capital": False,
        "priority_score": 95,
        "slug": "ubud-bali",
        "meta_description": "Discover Ubud, Bali's cultural heart. Experience rice terraces, traditional arts, yoga retreats, and spiritual temples in this enchanting Indonesian destination.",
        "keywords": ["ubud", "bali", "rice terraces", "yoga", "cultural", "spiritual", "indonesia", "monkey forest", "arts", "traditional"],
        "tracking": True
    },
    {
        "name": "Gili Trawangan",
        "display_name": "Gili Trawangan, Lombok",
        "local_name": "Gili Trawangan",
        "destination_type": "island",
        "state_province": "West Nusa Tenggara",
        "administrative_area": "North Lombok Regency",
        "latitude": -8.3492,
        "longitude": 116.0283,
        "description": "Gili Trawangan is the largest of the three Gili Islands off the northwest coast of Lombok, Indonesia. Known for its pristine white sand beaches, crystal-clear waters, vibrant marine life, and no motorized vehicles policy, it's a paradise for diving, snorkeling, and beach lovers.",
        "population": 800,
        "area_km2": 5.78,
        "elevation_m": 15,
        "tourist_rating": 4.5,
        "best_visit_months": [4, 5, 6, 7, 8, 9, 10],
        "climate_type": "Tropical savanna",
        "famous_attractions": [
            "Gili Trawangan Beach",
            "Turtle Point",
            "Sunset Point",
            "Gili T Wall (diving site)",
            "Shark Point (diving site)",
            "Night Market",
            "Swing at Sunset Point",
            "Glass Bottom Boat Tours"
        ],
        "timezone": "Asia/Makassar",
        "airport_codes": ["LOP"],
        "common_languages": ["Indonesian", "Sasak"],
        "external_ids": {
            "wikidata": "Q5561674",
            "geonames": "1642858"
        },
        "google_place_id": "ChIJK3qE5RXLzC0ROVu8cCQ_wpM",
        "is_active": True,
        "is_popular": True,
        "is_capital": False,
        "priority_score": 90,
        "slug": "gili-trawangan-lombok",
        "meta_description": "Escape to Gili Trawangan, the party island of the Gili Islands. Enjoy pristine beaches, world-class diving, vibrant nightlife, and car-free paradise.",
        "keywords": ["gili trawangan", "lombok", "diving", "snorkeling", "beach", "island", "party", "nightlife", "turtle", "coral"],
        "tracking": True
    },
    {
        "name": "Nusa Dua",
        "display_name": "Nusa Dua, Bali",
        "local_name": "Nusa Dua",
        "destination_type": "resort area",
        "state_province": "Bali",
        "administrative_area": "Badung Regency",
        "latitude": -8.8017,
        "longitude": 115.2289,
        "description": "Nusa Dua is an upscale resort area on the southern peninsula of Bali, Indonesia. Known for its luxurious hotels, pristine beaches, world-class golf courses, and the Bali Collection shopping center. It's designed as an enclave of international-standard resorts and is popular for conferences and upscale tourism.",
        "population": 15000,
        "area_km2": 350.0,
        "elevation_m": 10,
        "tourist_rating": 4.4,
        "best_visit_months": [4, 5, 6, 7, 8, 9, 10],
        "climate_type": "Tropical savanna",
        "famous_attractions": [
            "Nusa Dua Beach",
            "Bali Collection Shopping Center",
            "Museum Pasifika",
            "Puja Mandala (religious complex)",
            "Water Blow",
            "Bali National Golf Club",
            "Mengiat Beach",
            "Peninsula Island"
        ],
        "timezone": "Asia/Makassar",
        "airport_codes": ["DPS"],
        "common_languages": ["Indonesian", "Balinese"],
        "external_ids": {
            "wikidata": "Q3876620",
            "geonames": "1636544"
        },
        "google_place_id": "ChIJz6GHWys1wS0RABIBxEJTRBQ",
        "is_active": True,
        "is_popular": True,
        "is_capital": False,
        "priority_score": 85,
        "slug": "nusa-dua-bali",
        "meta_description": "Experience luxury at Nusa Dua, Bali's premier resort destination. Enjoy pristine beaches, world-class resorts, golf courses, and upscale shopping.",
        "keywords": ["nusa dua", "bali", "luxury", "resort", "beach", "golf", "shopping", "conference", "upscale", "peninsula"],
        "tracking": True
    }
]

async def seed_destinations():
    """Seed the destinations table with Indonesian destination data"""
    
    # Initialize Tortoise ORM
    db_url = settings.DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Handle PostgreSQL URL format
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)

    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["models.models"],
                "default_connection": "default",
            },
        },
    }

    print(f"🏝️ Seeding Indonesian destinations...")
    print(f"Connecting to database: {db_url}")
    await Tortoise.init(config=TORTOISE_ORM)

    # Get Indonesia country
    indonesia = await Country.get_or_none(iso_code_2="ID")
    if not indonesia:
        print("❌ Indonesia not found in countries table. Please run country seeding first.")
        await Tortoise.close_connections()
        return

    print(f"✅ Found Indonesia: {indonesia.name}")

    # Check existing destinations
    existing_count = await Destination.all().count()
    if existing_count > 0:
        print(f"Found {existing_count} existing destinations")
        confirm = input("Do you want to clear existing destinations and reseed? (y/N): ")
        if confirm.lower() == 'y':
            await Destination.all().delete()
            print("Cleared existing destination data")
        else:
            print("Skipping seed - keeping existing data")
            await Tortoise.close_connections()
            return

    # Insert destination data
    destinations_created = 0
    
    for dest_data in DESTINATIONS_DATA:
        try:
            # Add country reference
            dest_data["country"] = indonesia
            
            destination = await Destination.create(**dest_data)
            destinations_created += 1
            
            status = "🏝️" if destination.destination_type == "island" else "🏛️" if destination.destination_type == "town" else "🏨"
            attractions_count = len(destination.famous_attractions) if destination.famous_attractions else 0
            print(f"{status} Created: {destination.display_name} - {attractions_count} attractions - Rating: {destination.tourist_rating}")
            
        except Exception as e:
            print(f"❌ Failed to create {dest_data['name']}: {e}")

    print(f"\n🎉 Successfully created {destinations_created} destinations")
    
    # Verify data
    total_destinations = await Destination.all().count()
    popular_destinations = await Destination.filter(is_popular=True).count()
    
    print(f"📊 Database now contains:")
    print(f"   - Total destinations: {total_destinations}")
    print(f"   - Popular destinations: {popular_destinations}")
    
    # Show created destinations with details
    print(f"\n🏝️ Created Indonesian destinations:")
    created_destinations = await Destination.filter(country=indonesia).prefetch_related('country').all()
    for dest in created_destinations:
        attractions = len(dest.famous_attractions) if dest.famous_attractions else 0
        months = len(dest.best_visit_months) if dest.best_visit_months else 0
        print(f"   - {dest.display_name}")
        print(f"     Type: {dest.destination_type.title()} | Rating: {dest.tourist_rating}/5")
        print(f"     Location: {dest.latitude}, {dest.longitude}")
        print(f"     Best visit: {months} months | Attractions: {attractions}")
        print(f"     Tracking: {'Yes' if dest.tracking else 'No'} | Popular: {'Yes' if dest.is_popular else 'No'}")
        print()

    await Tortoise.close_connections()
    print("✅ Destination seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_destinations())