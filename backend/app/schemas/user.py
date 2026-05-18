"""用户相关 Schema"""
from typing import Optional
from pydantic import BaseModel


class WatchlistItemOut(BaseModel):
    code: str
    name: str
    close: float
    change_pct: float
    matched_pattern: Optional[str] = None
    in_observe_pool: bool = False


class WatchlistAddIn(BaseModel):
    code: str


class WatchlistUpdateIn(BaseModel):
    in_observe_pool: bool
