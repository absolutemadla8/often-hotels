from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status

from app import crud, models, schemas
from app.api.tortoise_deps import get_current_superuser, get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[schemas.UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Retrieve users. (Admin only)
    """
    users = await crud.user.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=schemas.UserResponse)
async def create_user(
    *,
    user_in: schemas.UserCreate,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Create new user. (Admin only)
    """
    user = await crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await crud.user.create(db, obj_in=user_in)
    return user


@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    *,
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Update a user. (Admin only)
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    user = await crud.user.update(db, db_obj=user, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user_by_id(
    user_id: int,
    current_user: models.User = Depends(get_current_active_user),
) -> Any:
    """
    Get a specific user by id.
    """
    user = await crud.user.get(db, id=user_id)
    if user == current_user:
        return user
    if not await crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return user


@router.delete("/{user_id}")
async def delete_user(
    *,
    user_id: int,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Delete a user. (Admin only)
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system",
        )
    if user == current_user:
        raise HTTPException(
            status_code=400, detail="Users cannot delete themselves"
        )
    await crud.user.remove(db, id=user_id)
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/activate")
async def activate_user(
    *,
    user_id: int,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Activate a user. (Admin only)
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = await crud.user.activate_user(db, user=user)
    return {"message": "User activated successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    *,
    user_id: int,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Deactivate a user. (Admin only)
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user == current_user:
        raise HTTPException(
            status_code=400, detail="Users cannot deactivate themselves"
        )
    
    user = await crud.user.deactivate_user(db, user=user)
    # Revoke all refresh tokens when deactivating
    await crud.refresh_token.revoke_user_tokens(db, user_id=user.id)
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/verify")
async def verify_user(
    *,
    user_id: int,
    current_user: models.User = Depends(get_current_superuser),
) -> Any:
    """
    Verify a user. (Admin only)
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = await crud.user.verify_user(db, user=user)
    return {"message": "User verified successfully"}