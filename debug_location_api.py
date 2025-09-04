#!/usr/bin/env python3
"""
Debug location API call
"""

import asyncio
import httpx
import sys
sys.path.insert(0, 'app')
from services.travclan_api_service import TravClanHotelApiService

async def test_with_requests_format():
    """Test using the exact format from the requests example"""
    
    # First get the token
    service = TravClanHotelApiService()
    async with service:
        token = await service.get_access_token()
        print(f"Got token: {token[:20]}...")
        
        # Test with exact headers from your example
        url = "https://hotel-api-sandbox.travclan.com/api/v1/locations/search/"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Authorization-Type": "external-service", 
            "source": "website"
        }
        params = {"searchString": "Kochi"}
        
        async with httpx.AsyncClient() as client:
            print(f"Making request to: {url}")
            print(f"Headers: {headers}")
            print(f"Params: {params}")
            
            response = await client.get(url, headers=headers, params=params)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success! Found {len(data.get('results', []))} locations")
                return True
            else:
                print("Failed!")
                return False

async def test_without_trailing_slash():
    """Test without trailing slash"""
    
    # First get the token
    service = TravClanHotelApiService()
    async with service:
        token = await service.get_access_token()
        
        # Test without trailing slash
        url = "https://hotel-api-sandbox.travclan.com/api/v1/locations/search"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Authorization-Type": "external-service", 
            "source": "website"
        }
        params = {"searchString": "Kochi"}
        
        async with httpx.AsyncClient() as client:
            print(f"Making request to: {url} (no trailing slash)")
            
            response = await client.get(url, headers=headers, params=params)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success! Found {len(data.get('results', []))} locations")
                return True
            else:
                print("Failed!")
                return False

async def main():
    print("🔍 Debugging TravClan Location API")
    print("=" * 50)
    
    print("\nTest 1: With trailing slash (like your example)")
    success1 = await test_with_requests_format()
    
    print("\nTest 2: Without trailing slash")  
    success2 = await test_without_trailing_slash()
    
    if success1 or success2:
        print("\n✅ Found working format!")
    else:
        print("\n❌ Both formats failed")

if __name__ == "__main__":
    asyncio.run(main())