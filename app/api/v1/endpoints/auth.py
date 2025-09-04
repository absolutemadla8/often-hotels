from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import deps
from app.core import auth, security
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    InvalidTokenException,
    ValidationException,
)

router = APIRouter()


@router.post("/register", response_model=schemas.UserResponse)
async def register(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register a new user.
    """
    try:
        user = await auth.register_user(db, user_data=user_in)
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
    db: AsyncSession = Depends(deps.get_db),
    user_credentials: schemas.UserLogin,
    request: Request,
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    try:
        user = await auth.authenticate_user(
            db, email=user_credentials.email, password=user_credentials.password
        )
        
        # Get client info for token tracking
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        
        token = await auth.create_user_tokens(
            db, user=user, user_agent=user_agent, ip_address=ip_address
        )
        
        return token
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
    db: AsyncSession = Depends(deps.get_db),
    token_data: schemas.TokenRefresh,
) -> Any:
    """
    Refresh access token using refresh token.
    """
    try:
        token = await auth.refresh_access_token(db, refresh_token=token_data.refresh_token)
        return token
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
    db: AsyncSession = Depends(deps.get_db),
    token_data: schemas.TokenRefresh,
    current_user: schemas.UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Logout user by revoking refresh token.
    """
    success = await auth.logout_user(db, refresh_token=token_data.refresh_token)
    if success:
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )


@router.post("/logout-all")
async def logout_all(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: schemas.UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Logout user from all devices by revoking all refresh tokens.
    """
    revoked_count = await auth.logout_all_devices(db, user_id=current_user.id)
    return {"message": f"Successfully logged out from {revoked_count} devices"}


@router.post("/change-password")
async def change_password(
    *,
    db: AsyncSession = Depends(deps.get_db),
    password_data: schemas.UserUpdatePassword,
    current_user: schemas.UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Change user password.
    """
    try:
        await auth.change_password(db, user=current_user, password_data=password_data)
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
    current_user: schemas.UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserUpdate,
    current_user: schemas.UserResponse = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    user = await crud.user.update(db, db_obj=current_user, obj_in=user_in)
    return user


# Password reset functionality (requires email service to be configured)
@router.post("/password-reset-request")
async def request_password_reset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    reset_request: schemas.PasswordResetRequest,
) -> Any:
    """
    Request password reset token (requires email service).
    """
    user = await crud.user.get_by_email(db, email=reset_request.email)
    if user:
        # In production, send email with reset token
        reset_token = security.create_password_reset_token(user.email)
        await crud.user.set_password_reset_token(db, user=user, token=reset_token)
        
    # Always return success for security (don't reveal if email exists)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset")
async def reset_password(
    *,
    db: AsyncSession = Depends(deps.get_db),
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
    
    user = await crud.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password and clear reset token
    user_update = schemas.UserUpdate(password=reset_data.new_password)
    await crud.user.update(db, db_obj=user, obj_in=user_update)
    await crud.user.set_password_reset_token(db, user=user, token=None)
    
    # Revoke all refresh tokens for security
    await crud.refresh_token.revoke_user_tokens(db, user_id=user.id)
    
    return {"message": "Password reset successfully"}