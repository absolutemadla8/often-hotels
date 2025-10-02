from datetime import timedelta, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app import schemas
from app.api.tortoise_deps import (
    get_current_active_user,
    get_current_user,
)
from app.core import security
from app.core.config import settings
from app.crud.tortoise_user import tortoise_user
from app.models.models import User
from app.models.models import RefreshToken
from app.core.exceptions import (
    AuthenticationException,
    InvalidTokenException,
    ValidationException,
)

router = APIRouter()


@router.post("/register", response_model=schemas.UserResponse)
async def register(
    *,
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register a new user.
    """
    try:
        # Check if user already exists
        existing_user = await tortoise_user.get_by_email(email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        user = await tortoise_user.create(obj_in=user_in)
        return user
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )


@router.post("/login", response_model=schemas.Token)
async def login(
    *,
    user_credentials: schemas.UserLogin,
    request: Request,
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    try:
        user = await tortoise_user.authenticate(
            email=user_credentials.email,
            password=user_credentials.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get client info for token tracking
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        # Create tokens - give admin user 1-year token, others get default
        if user.email == "trippy@oftenhotels.com" and user.is_superuser:
            # 1-year token for admin user
            access_token_expires = timedelta(days=365)
        else:
            # Default token duration for regular users
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        access_token = security.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = security.create_refresh_token(
            data={"sub": str(user.id)}, expires_delta=refresh_token_expires
        )

        # Store refresh token
        refresh_token_expires_at = datetime.utcnow() + refresh_token_expires
        await RefreshToken.create(
            user=user,
            token=refresh_token,
            expires_at=refresh_token_expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        # Calculate expires_in based on actual token duration
        if user.email == "trippy@oftenhotels.com" and user.is_superuser:
            expires_in_seconds = 365 * 24 * 60 * 60  # 1 year in seconds
        else:
            expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Default in seconds
            
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in_seconds
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(
    *,
    token_data: schemas.TokenRefresh,
) -> Any:
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = security.decode_token(token_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = int(payload.get("sub"))
        user = await tortoise_user.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Check if refresh token exists in database
        refresh_token_obj = await RefreshToken.get_or_none(token=token_data.refresh_token, user=user)
        if not refresh_token_obj or not refresh_token_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "refresh_token": token_data.refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    *,
    token_data: schemas.TokenRefresh,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Logout user by revoking refresh token.
    """
    refresh_token_obj = await RefreshToken.get_or_none(token=token_data.refresh_token, user=current_user)
    if refresh_token_obj:
        refresh_token_obj.is_active = False
        await refresh_token_obj.save()
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )


@router.post("/logout-all")
async def logout_all(
    *,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Logout user from all devices by revoking all refresh tokens.
    """
    refresh_tokens = await RefreshToken.filter(user=current_user, is_active=True)
    revoked_count = 0
    for token in refresh_tokens:
        token.is_active = False
        await token.save()
        revoked_count += 1
    return {"message": f"Successfully logged out from {revoked_count} devices"}


@router.post("/change-password")
async def change_password(
    *,
    password_data: schemas.UserUpdatePassword,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Change user password.
    """
    try:
        # Verify current password
        if not security.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )

        # Update password
        current_user.hashed_password = security.get_password_hash(password_data.new_password)
        await current_user.save()
        return {"message": "Password changed successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password"
        )


@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
async def update_user_me(
    *,
    user_in: schemas.UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    user = await tortoise_user.update(current_user, obj_in=user_in)
    return user


# Password reset functionality (requires email service to be configured)
@router.post("/password-reset-request")
async def request_password_reset(
    *,
    reset_request: schemas.PasswordResetRequest,
) -> Any:
    """
    Request password reset token (requires email service).
    """
    user = await tortoise_user.get_by_email(email=reset_request.email)
    if user:
        # In production, send email with reset token
        reset_token = security.create_password_reset_token(user.email)
        # Store reset token in user model (add field if needed)
        user.password_reset_token = reset_token
        await user.save()

    # Always return success for security (don't reveal if email exists)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset")
async def reset_password(
    *,
    reset_data: schemas.PasswordReset,
) -> Any:
    """
    Reset password using reset token.
    """
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    email = security.verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user = await tortoise_user.get_by_email(email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update password and clear reset token
    user.hashed_password = security.get_password_hash(reset_data.new_password)
    user.password_reset_token = None
    await user.save()

    return {"message": "Password reset successfully"}
    user_update = schemas.UserUpdate(password=reset_data.new_password)
    await crud.user.update(db, db_obj=user, obj_in=user_update)
    await crud.user.set_password_reset_token(db, user=user, token=None)
    
    # Revoke all refresh tokens for security
    await crud.refresh_token.revoke_user_tokens(db, user_id=user.id)
    
    return {"message": "Password reset successfully"}