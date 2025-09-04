from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core import security
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    InactiveUserException,
    InvalidTokenException,
    UnverifiedUserException,
    UserAlreadyExistsException,
    ValidationException,
)


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> models.User:
    """
    Authenticate user with email and password
    """
    user = await crud.user.authenticate(db, email=email, password=password)
    if not user:
        raise AuthenticationException("Incorrect email or password")
    
    if not await crud.user.is_active(user):
        raise InactiveUserException()
    
    return user


async def create_user_tokens(
    db: AsyncSession,
    user: models.User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> schemas.Token:
    """
    Create access and refresh tokens for user
    """
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    
    # Store refresh token in database
    await crud.refresh_token.create_refresh_token(
        db,
        user_id=user.id,
        token=refresh_token,
        expires_in_minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    # Update last login
    await crud.user.update_last_login(db, user=user)
    
    return schemas.Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


async def refresh_access_token(
    db: AsyncSession, refresh_token: str
) -> schemas.Token:
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    user_id = security.verify_token(refresh_token, token_type="refresh")
    if not user_id:
        raise InvalidTokenException("Invalid refresh token")
    
    # Check if refresh token exists in database
    stored_token = await crud.refresh_token.get_by_token(db, token=refresh_token)
    if not stored_token:
        raise InvalidTokenException("Refresh token not found or expired")
    
    # Get user
    user = await crud.user.get(db, id=int(user_id))
    if not user:
        raise AuthenticationException("User not found")
    
    if not await crud.user.is_active(user):
        raise InactiveUserException()
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    return schemas.Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


async def register_user(
    db: AsyncSession, user_data: schemas.UserCreate
) -> models.User:
    """
    Register a new user
    """
    # Validate passwords match
    if user_data.password != user_data.confirm_password:
        raise ValidationException("Passwords do not match")
    
    # Check if user already exists
    existing_user = await crud.user.get_by_email(db, email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException("Email already registered")
    
    # Check if username is taken (if provided)
    if user_data.username:
        existing_username = await crud.user.get_by_username(db, username=user_data.username)
        if existing_username:
            raise UserAlreadyExistsException("Username already taken")
    
    # Create user
    user = await crud.user.create(db, obj_in=user_data)
    
    return user


async def logout_user(
    db: AsyncSession, refresh_token: str
) -> bool:
    """
    Logout user by revoking refresh token
    """
    return await crud.refresh_token.revoke_token(db, token=refresh_token)


async def logout_all_devices(
    db: AsyncSession, user_id: int
) -> int:
    """
    Logout user from all devices by revoking all refresh tokens
    """
    return await crud.refresh_token.revoke_user_tokens(db, user_id=user_id)


async def change_password(
    db: AsyncSession, user: models.User, password_data: schemas.UserUpdatePassword
) -> models.User:
    """
    Change user password
    """
    # Verify current password
    if not security.verify_password(password_data.current_password, user.hashed_password):
        raise AuthenticationException("Current password is incorrect")
    
    # Validate new passwords match
    if password_data.new_password != password_data.confirm_new_password:
        raise ValidationException("New passwords do not match")
    
    # Update password
    user_update = schemas.UserUpdate(password=password_data.new_password)
    updated_user = await crud.user.update(db, db_obj=user, obj_in=user_update)
    
    # Revoke all refresh tokens for security
    await crud.refresh_token.revoke_user_tokens(db, user_id=user.id)
    
    return updated_user