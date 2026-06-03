"""持仓股 Schema"""
from pydantic import BaseModel, Field


class HoldingOut(BaseModel):
    id: int
    code: str
    name: str
    cost_price: float
    shares: int
    total_assets: float
    current_price: float | None = None
    profit_amount: float | None = None
    profit_pct: float | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class HoldingCreateIn(BaseModel):
    code: str = Field(..., description="股票代码")
    cost_price: float = Field(..., ge=0, description="成本价")
    shares: int = Field(..., ge=0, description="持仓数量")
    total_assets: float = Field(..., ge=0, description="总资产")


class HoldingUpdateIn(BaseModel):
    cost_price: float | None = None
    shares: int | None = None


class HoldingListOut(BaseModel):
    items: list[HoldingOut]
    total: int
