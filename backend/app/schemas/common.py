"""通用响应模型"""
from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
