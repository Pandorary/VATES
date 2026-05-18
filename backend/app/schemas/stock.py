"""股票相关 Schema"""
from typing import List, Optional
from pydantic import BaseModel


class StockSearchResult(BaseModel):
    code: str
    name: str
    industry: str
    close: float
    change_pct: float


class StockDetailOut(BaseModel):
    code: str
    name: str
    industry: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_pct: float
    turnover_rate: float
    sector_strength: float = 0


class KlineItem(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
