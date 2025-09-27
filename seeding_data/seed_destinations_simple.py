#!/usr/bin/env python3

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tortoise import Tortoise
from core.config import settings
from models.models import Country

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
        "tracking": True,
        "numberofdaystotrack": 30
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
        "tracking": True,
        "numberofdaystotrack": 30
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
        "tracking": True,
        "numberofdaystotrack": 30
    }
]

async def seed_destinations():
    """Seed the destinations table with Indonesian destination data using raw SQL"""
    
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
    from tortoise import connections
    db = connections.get("default")
    
    existing_result = await db.execute_query("SELECT COUNT(*) FROM destinations")
    existing_count = existing_result[1][0][0]
    
    if existing_count > 0:
        print(f"Found {existing_count} existing destinations")
        confirm = input("Do you want to clear existing destinations and reseed? (y/N): ")
        if confirm.lower() == 'y':
            await db.execute_query("DELETE FROM destinations")
            print("Cleared existing destination data")
        else:
            print("Skipping seed - keeping existing data")
            await Tortoise.close_connections()
            return

    # Insert destination data using raw SQL
    destinations_created = 0
    
    for dest_data in DESTINATIONS_DATA:
        try:
            # Prepare SQL INSERT statement
            sql = """
            INSERT INTO destinations (
                country_id, name, display_name, local_name, destination_type, 
                state_province, administrative_area, latitude, longitude, description,
                population, area_km2, elevation_m, tourist_rating, best_visit_months,
                climate_type, famous_attractions, timezone, airport_codes, common_languages,
                external_ids, google_place_id, is_active, is_popular, is_capital,
                priority_score, slug, meta_description, keywords, tracking, numberofdaystotrack,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33
            )
            """
            
            values = [
                indonesia.id,
                dest_data["name"],
                dest_data["display_name"],
                dest_data["local_name"],
                dest_data["destination_type"],
                dest_data["state_province"],
                dest_data["administrative_area"],
                dest_data["latitude"],
                dest_data["longitude"],
                dest_data["description"],
                dest_data["population"],
                dest_data["area_km2"],
                dest_data["elevation_m"],
                dest_data["tourist_rating"],
                json.dumps(dest_data["best_visit_months"]),
                dest_data["climate_type"],
                json.dumps(dest_data["famous_attractions"]),
                dest_data["timezone"],
                json.dumps(dest_data["airport_codes"]),
                json.dumps(dest_data["common_languages"]),
                json.dumps(dest_data["external_ids"]),
                dest_data["google_place_id"],
                dest_data["is_active"],
                dest_data["is_popular"],
                dest_data["is_capital"],
                dest_data["priority_score"],
                dest_data["slug"],
                dest_data["meta_description"],
                json.dumps(dest_data["keywords"]),
                dest_data["tracking"],
                dest_data["numberofdaystotrack"],
                datetime.utcnow(),
                datetime.utcnow()
            ]
            
            await db.execute_query(sql, values)
            destinations_created += 1
            
            status = "🏝️" if dest_data["destination_type"] == "island" else "🏛️" if dest_data["destination_type"] == "town" else "🏨"
            attractions_count = len(dest_data["famous_attractions"]) if dest_data["famous_attractions"] else 0
            print(f"{status} Created: {dest_data['display_name']} - {attractions_count} attractions - Rating: {dest_data['tourist_rating']}")
            
        except Exception as e:
            print(f"❌ Failed to create {dest_data['name']}: {e}")

    print(f"\n🎉 Successfully created {destinations_created} destinations")
    
    # Verify data
    total_result = await db.execute_query("SELECT COUNT(*) FROM destinations")
    total_destinations = total_result[1][0][0]
    
    popular_result = await db.execute_query("SELECT COUNT(*) FROM destinations WHERE is_popular = true")
    popular_destinations = popular_result[1][0][0]
    
    print(f"📊 Database now contains:")
    print(f"   - Total destinations: {total_destinations}")
    print(f"   - Popular destinations: {popular_destinations}")
    
    # Show created destinations with details
    print(f"\n🏝️ Created Indonesian destinations:")
    destinations_result = await db.execute_query("""
        SELECT d.display_name, d.destination_type, d.tourist_rating, d.latitude, d.longitude, 
               array_length(string_to_array(replace(replace(d.best_visit_months::text, '[', ''), ']', ''), ','), 1) as months_count,
               array_length(string_to_array(replace(replace(d.famous_attractions::text, '[', ''), ']', ''), ','), 1) as attractions_count,
               d.tracking, d.is_popular
        FROM destinations d 
        JOIN countries c ON d.country_id = c.id 
        WHERE c.iso_code_2 = 'ID'
    """)
    
    for row in destinations_result[1]:
        display_name, dest_type, rating, lat, lng, months_count, attractions_count, tracking, is_popular = row
        print(f"   - {display_name}")
        print(f"     Type: {dest_type.title()} | Rating: {rating}/5")
        print(f"     Location: {lat}, {lng}")
        print(f"     Best visit: {months_count or 0} months | Attractions: {attractions_count or 0}")
        print(f"     Tracking: {'Yes' if tracking else 'No'} | Popular: {'Yes' if is_popular else 'No'}")
        print()

    await Tortoise.close_connections()
    print("✅ Destination seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_destinations())