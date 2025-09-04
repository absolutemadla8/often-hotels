from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class ResponseBase(GenericModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None
    errors: Optional[List[Dict[str, Any]]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[List[Dict[str, Any]]] = None
    
    
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class PaginatedResponse(GenericModel, Generic[T]):
    success: bool = True
    message: str = "Data retrieved successfully"
    data: List[T]
    pagination: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str
    environment: str