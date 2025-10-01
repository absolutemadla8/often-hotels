"""
Itinerary Optimization API Endpoints

FastAPI endpoints for multi-destination itinerary optimization with
flexible search modes and hotel cost minimization.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.api.tortoise_deps import get_current_active_user
from app.models.models import User
from app.services.itinerary_optimization_service import (
    get_itinerary_optimization_service, ItineraryOptimizationService
)
from app.schemas.itinerary import (
    ItineraryOptimizationRequest, ItineraryOptimizationResponse,
    ItineraryErrorResponse
)
from app.core.data_filter import create_filtered_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/optimize")
async def optimize_itinerary(
    request: ItineraryOptimizationRequest,
    background_tasks: BackgroundTasks,
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for testing
    optimization_service: ItineraryOptimizationService = Depends(get_itinerary_optimization_service)
) -> JSONResponse:
    """
    Optimize multi-destination itinerary with flexible search modes
    
    **Search Modes:**
    - `custom=false`: Normal search only (start/mid/end of month)
    - `custom=true` + `search_types`: Custom search modes
    
    **Search Types:**
    - `"normal"`: Generate start/mid/end month itineraries
    - `"ranges"`: Sliding window across provided date ranges
    - `"fixed_dates"`: Exact start dates optimization
    - `"all"`: All search types combined
    
    **Optimization Features:**
    - Consecutive destination visits in specified order
    - Hotel cost minimization with single-hotel preference
    - Multi-currency support with conversion
    - Redis caching for improved performance
    - Comprehensive optimization metadata
    
    **Example Request:**
    ```json
    {
      "custom": true,
      "search_types": ["normal", "ranges"],
      "destinations": [
        {"destination_id": 101, "nights": 2},
        {"destination_id": 102, "nights": 3}
      ],
      "global_date_range": {
        "start": "2025-11-01",
        "end": "2025-11-30"
      },
      "ranges": [
        {"start": "2025-11-01", "end": "2025-11-15"},
        {"start": "2025-11-15", "end": "2025-11-30"}
      ],
      "guests": {"adults": 2, "children": 0},
      "currency": "USD",
      "top_k": 3
    }
    ```
    """
    try:
        # Temporarily use None for user during testing
        current_user = None
        user_id = "test_user"
        
        logger.info(f"User {user_id} requested itinerary optimization")
        logger.debug(f"Request: {request.model_dump()}")
        
        # Validate request parameters
        if request.custom and not request.search_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="search_types required when custom=true"
            )
        
        if "ranges" in request.search_types and not request.ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ranges parameter required for ranges search"
            )
        
        if "fixed_dates" in request.search_types and not request.fixed_dates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fixed_dates parameter required for fixed_dates search"
            )
        
        # Execute optimization
        result = await optimization_service.optimize_itinerary(request, current_user)
        
        # Schedule background tasks for analytics/logging
        background_tasks.add_task(
            _log_optimization_request, 
            user_id, 
            request, 
            result.success
        )
        
        if result.success:
            logger.info(
                f"Optimization successful for user {user_id}: "
                f"{result.metadata.processing_time_ms}ms, "
                f"best cost: {result.best_itinerary.total_cost if result.best_itinerary else 'N/A'}"
            )
        else:
            logger.warning(f"Optimization failed for user {user_id}")
        
        # Apply user access filtering
        return create_filtered_response(
            data=result.model_dump(),
            user=current_user,
            endpoint_path="/itineraries/optimize"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Itinerary optimization failed for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )


@router.get("/cached/{request_hash}")
async def get_cached_optimization(
    request_hash: str,
    # current_user: User = Depends(get_current_active_user),  # Temporarily disabled for testing
    optimization_service: ItineraryOptimizationService = Depends(get_itinerary_optimization_service)
) -> Dict[str, Any]:
    """
    Retrieve cached optimization result by request hash
    
    Useful for retrieving previously computed optimization results
    without re-running the expensive optimization process.
    
    **Parameters:**
    - `request_hash`: SHA256 hash of the optimization request
    
    **Returns:**
    - Cached optimization result or 404 if not found
    """
    try:
        cached_result = await optimization_service._get_cached_result(request_hash)
        
        if not cached_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cached result found for hash {request_hash}"
            )
        
        logger.info(f"User test_user retrieved cached result {request_hash[:8]}")
        
        return {
            "success": True,
            "data": cached_result,
            "message": f"Retrieved cached optimization result"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve cached result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cached result: {str(e)}"
        )


@router.post("/compare")
async def compare_search_types(
    request: ItineraryOptimizationRequest,
    current_user: User = Depends(get_current_active_user),
    optimization_service: ItineraryOptimizationService = Depends(get_itinerary_optimization_service)
) -> Dict[str, Any]:
    """
    Compare results across all available search types
    
    Automatically runs all search types (normal, ranges, fixed_dates) and
    provides a comprehensive comparison with cost analysis and recommendations.
    
    **Features:**
    - Runs all search modes automatically
    - Cost comparison across search types
    - Best value recommendations
    - Optimization statistics and metadata
    
    **Note:** This endpoint ignores the `custom` and `search_types` parameters
    and always runs all available search types for comparison.
    """
    try:
        # Force all search types for comparison
        comparison_request = request.model_copy(update={
            "custom": True,
            "search_types": ["all"]
        })
        
        logger.info(f"User {current_user.id} requested search type comparison")
        
        # Execute optimization with all search types
        result = await optimization_service.optimize_itinerary(comparison_request, current_user)
        
        if not result.success:
            return {
                "success": False,
                "message": "Comparison failed",
                "errors": getattr(result, 'errors', [])
            }
        
        # Analyze and compare results
        comparison_analysis = _analyze_search_type_results(result)
        
        logger.info(f"Search type comparison completed for user {current_user.id}")
        
        return {
            "success": True,
            "optimization_result": result,
            "comparison_analysis": comparison_analysis,
            "message": "Search type comparison completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Search type comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/history")
async def get_user_optimization_history(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get user's optimization history
    
    Returns a paginated list of the user's previous optimization requests
    with summary information and cache status.
    
    **Parameters:**
    - `limit`: Maximum number of records to return (default: 10, max: 50)
    - `offset`: Number of records to skip (default: 0)
    
    **Returns:**
    - List of optimization history records with metadata
    """
    try:
        from app.models.models import ItinerarySearchRequest
        
        # Validate parameters
        limit = min(max(limit, 1), 50)  # Clamp between 1 and 50
        offset = max(offset, 0)
        
        # Query user's search history
        history_query = ItinerarySearchRequest.filter(
            user=current_user
        ).order_by('-created_at')
        
        # Get total count and paginated results
        total_count = await history_query.count()
        history_records = await history_query.offset(offset).limit(limit).all()
        
        # Format response
        history_data = []
        for record in history_records:
            history_data.append({
                "request_hash": record.request_hash,
                "search_types": record.search_types,
                "destinations_count": len(record.destinations),
                "itineraries_generated": record.itineraries_generated,
                "best_cost": record.best_cost,
                "currency": record.currency,
                "processing_time_ms": record.processing_time_ms,
                "cache_hit": record.cache_hit,
                "access_count": record.access_count,
                "created_at": record.created_at.isoformat(),
                "last_accessed": record.last_accessed.isoformat()
            })
        
        logger.info(f"Retrieved {len(history_data)} history records for user {current_user.id}")
        
        return {
            "success": True,
            "data": history_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "message": f"Retrieved {len(history_data)} optimization history records"
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve optimization history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@router.delete("/cache/{request_hash}")
async def clear_cached_optimization(
    request_hash: str,
    current_user: User = Depends(get_current_active_user),
    optimization_service: ItineraryOptimizationService = Depends(get_itinerary_optimization_service)
) -> Dict[str, Any]:
    """
    Clear specific cached optimization result
    
    Removes a cached optimization result by request hash.
    Useful for clearing outdated results or testing.
    
    **Parameters:**
    - `request_hash`: SHA256 hash of the optimization request to clear
    
    **Returns:**
    - Success confirmation
    """
    try:
        cache_service = await optimization_service._get_services()
        cache_key = f"itinerary_optimization:{request_hash}"
        
        deleted = await optimization_service._cache_service.delete(cache_key)
        
        if deleted:
            logger.info(f"User {current_user.id} cleared cached result {request_hash[:8]}")
            message = f"Cached result cleared successfully"
        else:
            message = f"No cached result found for hash {request_hash}"
        
        return {
            "success": True,
            "deleted": deleted,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cached result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


# Helper functions
async def _log_optimization_request(
    user_id: int, 
    request: ItineraryOptimizationRequest, 
    success: bool
):
    """Background task to log optimization request for analytics"""
    try:
        # This would typically log to analytics system or database
        logger.info(
            f"Analytics: User {user_id} optimization "
            f"{'succeeded' if success else 'failed'}, "
            f"destinations: {len(request.destinations)}, "
            f"search_types: {request.search_types}"
        )
    except Exception as e:
        logger.error(f"Failed to log optimization request: {e}")


def _analyze_search_type_results(result: ItineraryOptimizationResponse) -> Dict[str, Any]:
    """Analyze and compare results across search types"""
    analysis = {
        "search_types_executed": [],
        "cost_comparison": {},
        "recommendations": [],
        "best_overall": None
    }
    
    # Collect all itineraries
    all_itineraries = []
    
    if result.normal:
        analysis["search_types_executed"].append("normal")
        normal_itineraries = [
            result.normal.start_month,
            result.normal.mid_month,
            result.normal.end_month
        ]
        valid_normal = [i for i in normal_itineraries if i]
        all_itineraries.extend(valid_normal)
        
        if valid_normal:
            costs = [i.total_cost for i in valid_normal]
            analysis["cost_comparison"]["normal"] = {
                "count": len(valid_normal),
                "min_cost": min(costs),
                "max_cost": max(costs),
                "avg_cost": sum(costs) / len(costs)
            }
    
    if result.ranges:
        analysis["search_types_executed"].append("ranges")
        all_itineraries.extend(result.ranges.results)
        
        costs = [i.total_cost for i in result.ranges.results]
        if costs:
            analysis["cost_comparison"]["ranges"] = {
                "count": len(costs),
                "min_cost": min(costs),
                "max_cost": max(costs),
                "avg_cost": sum(costs) / len(costs)
            }
    
    if result.fixed_dates:
        analysis["search_types_executed"].append("fixed_dates")
        all_itineraries.extend(result.fixed_dates.results)
        
        costs = [i.total_cost for i in result.fixed_dates.results]
        if costs:
            analysis["cost_comparison"]["fixed_dates"] = {
                "count": len(costs),
                "min_cost": min(costs),
                "max_cost": max(costs),
                "avg_cost": sum(costs) / len(costs)
            }
    
    # Find best overall
    if all_itineraries:
        best = min(all_itineraries, key=lambda x: x.total_cost)
        analysis["best_overall"] = {
            "search_type": best.search_type,
            "label": best.label,
            "total_cost": best.total_cost,
            "currency": best.currency,
            "start_date": best.start_date.isoformat(),
            "end_date": best.end_date.isoformat()
        }
    
    # Generate recommendations
    if len(analysis["cost_comparison"]) > 1:
        search_type_costs = {
            st: data["min_cost"] 
            for st, data in analysis["cost_comparison"].items()
        }
        cheapest_search_type = min(search_type_costs.keys(), key=lambda k: search_type_costs[k])
        analysis["recommendations"].append(
            f"'{cheapest_search_type}' search offers the lowest cost option"
        )
    
    return analysis