from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, locations, tracking, recommendations, tasks

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(tracking.router, tags=["tracking"])
api_router.include_router(recommendations.router, tags=["recommendations"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])