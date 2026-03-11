"""Common schemas used across the application."""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ErrorDetail(BaseModel):
    """Error response detail."""

    code: str
    message: str


class Page(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T]
    total: int
    skip: int
    limit: int

    def __init__(self, items: List[T], total: int, skip: int, limit: int):
        super().__init__(items=items, total=total, skip=skip, limit=limit)


class BaseResponse(BaseModel):
    """Base response model."""

    success: bool = True
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    message: Optional[str] = None
