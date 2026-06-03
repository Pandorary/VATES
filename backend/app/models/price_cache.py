"""价格缓存表 — DEPRECATED

已被 app.models.stock.StockQuote 替代。
holding.py 中的价格获取已迁移至 app.services.quotes 包。
保留此模型以兼容已有数据库，新代码请勿使用。
"""
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, func
from app.database import Base


class PriceCache(Base):
    __tablename__ = "price_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())