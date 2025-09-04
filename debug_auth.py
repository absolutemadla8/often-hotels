#!/usr/bin/env python3
"""
Debug TravClan authentication
"""

import asyncio
import httpx
import json

async def test_auth_payload_formats():
    """Test different authentication payload formats"""
    
    auth_url = "https://trav-auth-sandbox.travclan.com/authentication/internal/service/login"
    
    # Test different payload formats
    payloads = [
        # Format 1: Direct fields
        {
            "apiKey": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
            "merchantId": "mereigfvbl3", 
            "userId": "dda7b7cdb"
        },
        # Format 2: Camelcase variants
        {
            "api_key": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
            "merchant_id": "mereigfvbl3",
            "user_id": "dda7b7cdb"
        },
        # Format 3: Different field names
        {
            "key": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
            "merchantId": "mereigfvbl3",
            "userId": "dda7b7cdb"
        },
        # Format 4: All uppercase
        {
            "APIKEY": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
            "MERCHANTID": "mereigfvbl3",
            "USERID": "dda7b7cdb"
        }
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for i, payload in enumerate(payloads, 1):
            print(f"🧪 Testing payload format {i}: {json.dumps(payload, indent=2)}")
            
            try:
                response = await client.post(
                    auth_url,
                    headers={'Content-Type': 'application/json'},
                    json=payload
                )
                
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    print("   ✅ SUCCESS! This format worked")
                    return payload
                else:
                    print("   ❌ Failed")
                    
            except Exception as e:
                print(f"   💥 Error: {e}")
            
            print()
    
    return None


async def test_get_request():
    """Test if it's a GET request instead of POST"""
    auth_url = "https://trav-auth-sandbox.travclan.com/authentication/internal/service/login"
    
    print("🧪 Testing GET request...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                auth_url,
                params={
                    "apiKey": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
                    "merchantId": "mereigfvbl3",
                    "userId": "dda7b7cdb"
                }
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS! GET request worked")
                return True
                
        except Exception as e:
            print(f"   💥 Error: {e}")
    
    return False


async def test_form_data():
    """Test form data instead of JSON"""
    auth_url = "https://trav-auth-sandbox.travclan.com/authentication/internal/service/login"
    
    print("🧪 Testing form data...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                auth_url,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={
                    "apiKey": "9032b4cd-8c21-4d55-8c1f-d05487fce98a",
                    "merchantId": "mereigfvbl3",
                    "userId": "dda7b7cdb"
                }
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("   ✅ SUCCESS! Form data worked")
                return True
                
        except Exception as e:
            print(f"   💥 Error: {e}")
    
    return False


async def main():
    """Run authentication debugging"""
    print("🔐 TravClan Authentication Debug")
    print("=" * 50)
    
    # Test different payload formats
    success_payload = await test_auth_payload_formats()
    
    if not success_payload:
        # Test GET request
        if await test_get_request():
            print("✅ Use GET request instead of POST")
            return
        
        # Test form data
        if await test_form_data():
            print("✅ Use form data instead of JSON")
            return
    
    if success_payload:
        print(f"✅ Working payload format: {json.dumps(success_payload, indent=2)}")
    else:
        print("❌ No working authentication format found")
        print("\n💡 Suggestions:")
        print("   1. Check if the credentials are correct")
        print("   2. Verify the authentication endpoint URL")
        print("   3. Check if there are additional headers required")
        print("   4. Look for API documentation on the exact format")


if __name__ == "__main__":
    asyncio.run(main())