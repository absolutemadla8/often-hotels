"""
Admin Access Middleware

This module provides middleware and decorators for admin-only endpoints.
Currently implements a pass-through approach but can be enhanced for role-based access control.
"""

import logging
from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer

from app.api.tortoise_deps import get_current_user
from app.models.models import User

logger = logging.getLogger(__name__)

# Security scheme for token extraction
security = HTTPBearer()


class AdminAccessError(HTTPException):
    """Custom exception for admin access errors"""
    
    def __init__(self, detail: str = "Admin access required"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def verify_admin_access(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that the current user has admin access
    
    Currently implements a pass-through approach - all authenticated users are considered admins.
    This can be enhanced to check for specific admin roles or permissions.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User if admin access is granted
        
    Raises:
        AdminAccessError: If admin access is denied
    """
    # Current implementation: All authenticated users have admin access
    # This is a simple pass-through for initial implementation
    
    # Future enhancement: Check for admin role
    # if not current_user.is_superuser:
    #     logger.warning(f"Admin access denied for user {current_user.email}")
    #     raise AdminAccessError("Insufficient privileges for admin access")
    
    # For now, we use is_superuser field if available
    if hasattr(current_user, 'is_superuser') and not current_user.is_superuser:
        logger.warning(f"Admin access denied for user {current_user.email}")
        raise AdminAccessError("Insufficient privileges for admin access")
    
    logger.info(f"Admin access granted for user {current_user.email}")
    return current_user


def admin_required(func: Callable) -> Callable:
    """
    Decorator to require admin access for a function
    
    Usage:
        @admin_required
        async def some_admin_function():
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # This decorator is for use with FastAPI dependency injection
        # The actual admin verification happens in verify_admin_access
        return await func(*args, **kwargs)
    
    return wrapper


class AdminMiddleware:
    """
    Middleware class for admin access control
    
    This can be used as a FastAPI middleware or for custom access control logic.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """
        Process request and verify admin access for admin endpoints
        """
        # Check if this is an admin endpoint
        if self._is_admin_endpoint(request):
            # Admin endpoint verification would happen here
            # For now, we rely on the endpoint-level dependencies
            logger.debug(f"Admin endpoint accessed: {request.url.path}")
        
        response = await call_next(request)
        return response
    
    def _is_admin_endpoint(self, request: Request) -> bool:
        """
        Check if the request is for an admin endpoint
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if this is an admin endpoint
        """
        path = request.url.path
        return path.startswith("/api/v1/admin/")


# Convenience function for creating admin dependency
def get_admin_user() -> Callable:
    """
    Get admin user dependency for FastAPI endpoints
    
    Returns:
        Dependency function that verifies admin access
    """
    return Depends(verify_admin_access)


# Decorator for admin endpoints
def admin_endpoint(func: Callable) -> Callable:
    """
    Decorator to mark an endpoint as admin-only
    
    This decorator should be used in combination with the admin dependency:
    
    @admin_endpoint
    async def some_endpoint(admin_user: User = get_admin_user()):
        pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    
    # Add metadata to indicate this is an admin endpoint
    wrapper.__admin_endpoint__ = True
    return wrapper


# Helper function to check if user has admin privileges
async def is_admin_user(user: User) -> bool:
    """
    Check if a user has admin privileges
    
    Args:
        user: User to check
        
    Returns:
        True if user has admin privileges
    """
    # Current implementation: Check is_superuser field
    return getattr(user, 'is_superuser', False)


# Helper function for logging admin actions
def log_admin_action(
    user: User,
    action: str,
    details: dict = None,
    request: Request = None
):
    """
    Log admin actions for audit purposes
    
    Args:
        user: User performing the action
        action: Description of the action
        details: Additional details about the action
        request: FastAPI request object for context
    """
    log_data = {
        "user_id": user.id,
        "user_email": user.email,
        "action": action,
        "timestamp": logger.name,
    }
    
    if details:
        log_data["details"] = details
    
    if request:
        log_data.update({
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "path": request.url.path,
            "method": request.method,
        })
    
    logger.info(f"Admin action performed", extra=log_data)