"""市场相关 Schema"""
from typing import List, Optional
from pydantic import BaseModel


class SectorFlowSchema(BaseModel):
    sector: str
    net_inflow: float
    lead_stock: str


class MarketTempDetails(BaseModel):
    max_board_height: int
    promotion_rate: float
    bomb_rate: float
    yesterday_avg_return: float


class MarketTemperatureOut(BaseModel):
    trade_date: str
    status: str
    status_text: str
    advice: str
    details: MarketTempDetails
    main_flows: List[SectorFlowSchema] = []


# ---------- 行情页新增 ----------

class IndexItem(BaseModel):
    name: str          # 上证指数
    code: str          # 000001
    price: float       # 最新价
    change_pct: float  # 涨跌幅 %


class TopStock(BaseModel):
    code: str
    name: str
    close: float
    change_pct: float


class MarketOverview(BaseModel):
    indices: List[IndexItem]
    top_sectors: List[SectorFlowSchema]
    top_stocks: List[TopStock]


class AIOpportunityResponse(BaseModel):
    content: str


class AIRecommendResponse(BaseModel):
    content: str
