from typing import Dict, Any
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.travclan_api_service import travclan_api_service

router = APIRouter()


@router.get("/search")
async def search_locations(
    search_keyword: str = Query(..., min_length=2, description="Search keyword for locations"),
    db: AsyncSession = Depends(deps.get_db)
) -> Dict[str, Any]:
    """
    Search for hotel locations and destinations
    
    Search for destinations, cities, and clusters for hotel bookings
    """
    if len(search_keyword.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search keyword must be at least 2 characters")
    
    try:
        # Use async context manager for the API service
        async with travclan_api_service:
            response = await travclan_api_service.search_locations(search_keyword.strip())
        
        # Process API results
        api_results = process_api_results(response.get('results', []))
        
        return {
            "status": "success",
            "data": api_results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Location search failed: {str(e)}")


def process_api_results(results) -> list:
    """
    Process the API search results and format them
    """
    processed_results = []
    
    for result in results:
        # Remove travclanScore if present
        clean_result = {k: v for k, v in result.items() if k != 'travclanScore'}
        
        # For hotel type, use referenceId as the id if available
        result_id = result.get('id')
        if (result.get('type', '').upper() == 'HOTEL' and 
            result.get('referenceId') and result.get('referenceId') > 0):
            result_id = result.get('referenceId')
        
        processed_result = {
            'id': result_id,
            'type': result.get('type'),
            'name': result.get('name'),
            'city': result.get('city'),
            'state': result.get('state'),
            'country': result.get('country'),
            'coordinates': result.get('coordinates'),
            'fullName': result.get('fullName'),
            'source': 'api'
        }
        
        processed_results.append(processed_result)
    
    return processed_results