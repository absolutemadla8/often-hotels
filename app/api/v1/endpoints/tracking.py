from datetime import datetime, date
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.models.models import Tracker, TrackerResult
from app.services.tracking_service import HotelTrackingService, get_tracking_service
from app.services.serp_service import SearchCriteria, SortBy, Rating, HotelClass
from app.schemas.response import ResponseBase

router = APIRouter(prefix="/tracking", tags=["Tracking"])


class CreateTrackerRequest(BaseModel):
    name: str = Field(..., description="Tracker name")
    description: Optional[str] = Field(None, description="Tracker description")
    query: str = Field(..., description="Search query (hotel name, location, etc.)")
    start_date: date = Field(..., description="Start date for tracking")
    end_date: date = Field(..., description="End date for tracking")
    interval_days: int = Field(1, description="Interval between checks in days")
    stay_duration_days: int = Field(1, description="Length of stay in days")
    adults: int = Field(2, description="Number of adults")
    children: int = Field(0, description="Number of children")
    currency: str = Field("USD", description="Currency code")
    country_code: str = Field("us", description="Country code")
    language: str = Field("en", description="Language code")
    is_scheduled: bool = Field(True, description="Enable scheduled tracking")


class TrackerResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    tracker_type: str
    total_runs: int
    successful_runs: int
    last_run_at: Optional[datetime]
    created_at: datetime
    search_parameters: Optional[Dict[str, Any]]


class TrackerResultResponse(BaseModel):
    id: int
    tracker_id: int
    run_id: str
    success: bool
    items_found: int
    execution_time_seconds: float
    error_message: Optional[str]
    created_at: datetime


class RunTrackerRequest(BaseModel):
    tracker_ids: List[int] = Field(..., description="List of tracker IDs to run")


class TestSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    check_in_date: date = Field(..., description="Check-in date")
    check_out_date: date = Field(..., description="Check-out date")
    adults: int = Field(2, description="Number of adults")
    children: int = Field(0, description="Number of children")
    currency: str = Field("USD", description="Currency")
    country_code: str = Field("us", description="Country code")
    language: str = Field("en", description="Language code")


@router.post("/trackers", response_model=ResponseBase[TrackerResponse])
async def create_tracker(request: CreateTrackerRequest):
    """Create a new hotel price tracker"""
    try:
        # Prepare search parameters
        search_parameters = {
            "query": request.query,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "interval_days": request.interval_days,
            "stay_duration_days": request.stay_duration_days,
            "adults": request.adults,
            "children": request.children,
            "currency": request.currency,
            "country_code": request.country_code,
            "language": request.language,
        }

        # Create tracker with required fields
        tracker = await Tracker.create(
            name=request.name,
            description=request.description,
            tracker_type="hotel_search",
            start_date=request.start_date,
            end_date=request.end_date,
            trackable_items=[],  # Empty for now
            search_criteria=search_parameters,
            currency=request.currency,
            user_id=1,  # Default user for now - in production use authenticated user
        )

        response_data = TrackerResponse(
            id=tracker.id,
            name=tracker.name,
            description=tracker.description,
            status=tracker.status,
            tracker_type=tracker.tracker_type,
            total_runs=tracker.total_runs,
            successful_runs=tracker.successful_runs,
            last_run_at=tracker.last_run_at,
            created_at=tracker.created_at,
            search_parameters=tracker.search_criteria
        )

        return ResponseBase(
            success=True,
            message="Tracker created successfully",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create tracker: {str(e)}")


@router.get("/trackers", response_model=ResponseBase[List[TrackerResponse]])
async def list_trackers(
    status: Optional[str] = None,
    tracker_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List all trackers"""
    try:
        query = Tracker.all()

        if status:
            query = query.filter(status=status)

        if tracker_type:
            query = query.filter(tracker_type=tracker_type)

        trackers = await query.offset(offset).limit(limit).all()

        response_data = [
            TrackerResponse(
                id=tracker.id,
                name=tracker.name,
                description=tracker.description,
                status=tracker.status,
                tracker_type=tracker.tracker_type,
                total_runs=tracker.total_runs,
                successful_runs=tracker.successful_runs,
                last_run_at=tracker.last_run_at,
                created_at=tracker.created_at,
                search_parameters=tracker.search_criteria
            )
            for tracker in trackers
        ]

        return ResponseBase(
            success=True,
            message=f"Retrieved {len(response_data)} trackers",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trackers: {str(e)}")


@router.get("/trackers/{tracker_id}", response_model=ResponseBase[TrackerResponse])
async def get_tracker(tracker_id: int):
    """Get a specific tracker"""
    tracker = await Tracker.get_or_none(id=tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    response_data = TrackerResponse(
        id=tracker.id,
        name=tracker.name,
        description=tracker.description,
        status=tracker.status,
        tracker_type=tracker.tracker_type,
        total_runs=tracker.total_runs,
        successful_runs=tracker.successful_runs,
        last_run_at=tracker.last_run_at,
        created_at=tracker.created_at,
        search_parameters=tracker.search_criteria
    )

    return ResponseBase(
        success=True,
        message="Tracker retrieved successfully",
        data=response_data
    )


@router.put("/trackers/{tracker_id}", response_model=ResponseBase[TrackerResponse])
async def update_tracker(tracker_id: int, request: CreateTrackerRequest):
    """Update an existing tracker"""
    tracker = await Tracker.get_or_none(id=tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    try:
        # Update search parameters
        search_parameters = {
            "query": request.query,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "interval_days": request.interval_days,
            "stay_duration_days": request.stay_duration_days,
            "adults": request.adults,
            "children": request.children,
            "currency": request.currency,
            "country_code": request.country_code,
            "language": request.language,
        }

        # Update tracker
        tracker.name = request.name
        tracker.description = request.description
        tracker.search_criteria = search_parameters
        tracker.is_scheduled = request.is_scheduled
        tracker.updated_at = datetime.utcnow()

        await tracker.save()

        response_data = TrackerResponse(
            id=tracker.id,
            name=tracker.name,
            description=tracker.description,
            status=tracker.status,
            tracker_type=tracker.tracker_type,
            total_runs=tracker.total_runs,
            successful_runs=tracker.successful_runs,
            last_run_at=tracker.last_run_at,
            created_at=tracker.created_at,
            search_parameters=tracker.search_criteria
        )

        return ResponseBase(
            success=True,
            message="Tracker updated successfully",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update tracker: {str(e)}")


@router.delete("/trackers/{tracker_id}", response_model=ResponseBase[None])
async def delete_tracker(tracker_id: int):
    """Delete a tracker"""
    tracker = await Tracker.get_or_none(id=tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    try:
        await tracker.delete()
        return ResponseBase(
            success=True,
            message="Tracker deleted successfully",
            data=None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tracker: {str(e)}")


@router.post("/run", response_model=ResponseBase[List[TrackerResultResponse]])
async def run_trackers(
    request: RunTrackerRequest,
    background_tasks: BackgroundTasks,
    tracking_service: HotelTrackingService = Depends(get_tracking_service)
):
    """Run specific trackers manually"""
    try:
        # Validate tracker IDs
        trackers = []
        for tracker_id in request.tracker_ids:
            tracker = await Tracker.get_or_none(id=tracker_id)
            if not tracker:
                raise HTTPException(status_code=404, detail=f"Tracker {tracker_id} not found")
            trackers.append(tracker)

        # Run trackers
        results = await tracking_service.run_multiple_trackers(request.tracker_ids)

        response_data = [
            TrackerResultResponse(
                id=result.id,
                tracker_id=result.tracker_id,
                run_id=result.run_id,
                success=result.success,
                items_found=result.items_found,
                execution_time_seconds=result.execution_time_seconds,
                error_message=result.error_message,
                created_at=result.created_at
            )
            for result in results
        ]

        return ResponseBase(
            success=True,
            message=f"Executed {len(results)} trackers",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run trackers: {str(e)}")


@router.post("/run-scheduled", response_model=ResponseBase[List[TrackerResultResponse]])
async def run_scheduled_trackers(
    background_tasks: BackgroundTasks,
    tracking_service: HotelTrackingService = Depends(get_tracking_service)
):
    """Run all scheduled trackers that are due"""
    try:
        results = await tracking_service.run_scheduled_trackers()

        response_data = [
            TrackerResultResponse(
                id=result.id,
                tracker_id=result.tracker_id,
                run_id=result.run_id,
                success=result.success,
                items_found=result.items_found,
                execution_time_seconds=result.execution_time_seconds,
                error_message=result.error_message,
                created_at=result.created_at
            )
            for result in results
        ]

        return ResponseBase(
            success=True,
            message=f"Executed {len(results)} scheduled trackers",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scheduled trackers: {str(e)}")


@router.get("/trackers/{tracker_id}/results", response_model=ResponseBase[List[TrackerResultResponse]])
async def get_tracker_results(
    tracker_id: int,
    limit: int = 50,
    offset: int = 0
):
    """Get results for a specific tracker"""
    tracker = await Tracker.get_or_none(id=tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")

    try:
        results = await TrackerResult.filter(
            tracker_id=tracker_id
        ).order_by('-created_at').offset(offset).limit(limit).all()

        response_data = [
            TrackerResultResponse(
                id=result.id,
                tracker_id=result.tracker_id,
                run_id=result.run_id,
                success=result.success,
                items_found=result.items_found,
                execution_time_seconds=result.execution_time_seconds,
                error_message=result.error_message,
                created_at=result.created_at
            )
            for result in results
        ]

        return ResponseBase(
            success=True,
            message=f"Retrieved {len(response_data)} results",
            data=response_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.post("/test-search", response_model=ResponseBase[Dict[str, Any]])
async def test_search(
    request: TestSearchRequest,
    tracking_service: HotelTrackingService = Depends(get_tracking_service)
):
    """Test a search query without creating a tracker"""
    try:
        criteria = SearchCriteria(
            query=request.query,
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date,
            adults=request.adults,
            children=request.children,
            currency=request.currency,
            gl=request.country_code,
            hl=request.language
        )

        response = await tracking_service.serp_service.search_hotels(criteria)

        # Summarize results
        summary = {
            "total_properties": len(response.properties),
            "total_ads": len(response.ads),
            "search_metadata": {
                "status": response.search_metadata.status,
                "total_time_taken": response.search_metadata.time_taken
            }
        }

        if response.properties:
            prices = [
                prop.rate_per_night.extracted_lowest
                for prop in response.properties
                if prop.rate_per_night and prop.rate_per_night.extracted_lowest
            ]
            if prices:
                summary["price_range"] = {
                    "min": min(prices),
                    "max": max(prices),
                    "average": sum(prices) / len(prices)
                }

            summary["sample_properties"] = [
                {
                    "name": prop.name,
                    "type": prop.type,
                    "price": prop.rate_per_night.extracted_lowest if prop.rate_per_night else None,
                    "rating": prop.overall_rating,
                    "reviews": prop.reviews
                }
                for prop in response.properties[:5]  # First 5 properties
            ]

        return ResponseBase(
            success=True,
            message="Search test completed successfully",
            data=summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search test failed: {str(e)}")