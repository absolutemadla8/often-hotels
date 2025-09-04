import traceback
from typing import Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError, ValidationException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.response import ErrorResponse

logger = get_logger("error_handler")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with structured error response
    """
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            errors=[{
                "type": "HTTPException",
                "code": exc.status_code,
                "message": exc.detail
            }]
        ).dict(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with detailed field information
    """
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(x) for x in error.get("loc", []))
        errors.append({
            "type": "validation_error",
            "field": field_path,
            "message": error.get("msg", "Validation error"),
            "input": error.get("input"),
        })
    
    logger.warning(
        "Validation error occurred",
        errors=errors,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            message="Validation failed",
            errors=errors
        ).dict(),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle SQLAlchemy database errors
    """
    error_message = "Database error occurred"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(exc, IntegrityError):
        error_message = "Data integrity constraint violated"
        status_code = status.HTTP_409_CONFLICT
        
        # Extract useful information from integrity error
        if "unique constraint" in str(exc).lower():
            error_message = "Resource already exists"
        elif "foreign key constraint" in str(exc).lower():
            error_message = "Referenced resource does not exist"
        elif "check constraint" in str(exc).lower():
            error_message = "Data validation failed"
    
    logger.error(
        "Database error occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            message=error_message,
            errors=[{
                "type": "database_error",
                "message": error_message if status_code != 500 else "Internal server error"
            }]
        ).dict(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unhandled exceptions
    """
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            message="Internal server error",
            errors=[{
                "type": "internal_error",
                "message": "An unexpected error occurred"
            }]
        ).dict(),
    )


async def rate_limit_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle rate limiting errors
    """
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else None,
    )
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            success=False,
            message="Rate limit exceeded. Please try again later.",
            errors=[{
                "type": "rate_limit_error",
                "message": "Too many requests"
            }]
        ).dict(),
        headers={"Retry-After": "60"}  # Suggest retry after 60 seconds
    )


def setup_exception_handlers(app):
    """
    Setup all exception handlers for the FastAPI app
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Rate limiting (if using slowapi)
    try:
        from slowapi.errors import RateLimitExceeded
        app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    except ImportError:
        pass