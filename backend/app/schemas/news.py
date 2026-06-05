"""资讯 Schema"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class NewsOut(BaseModel):
    id: int
    code: str | None = None
    title: str
    url: str | None = None
    source_site: str | None = None
    publish_time: datetime | None = None
    content_preview: str | None = None

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    items: List[NewsOut]
    total: int
    page: int
    page_size: int
