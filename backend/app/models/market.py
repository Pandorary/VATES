"""市场相关模型"""
from sqlalchemy import Column, Date, Integer, Numeric, String, Text, TIMESTAMP, func
from app.database import Base


class MarketSentiment(Base):
    __tablename__ = "market_sentiment"
    trade_date = Column(Date, primary_key=True)
    max_board_height = Column(Integer)
    promotion_rate = Column(Numeric(6, 4))
    bomb_rate = Column(Numeric(6, 4))
    yesterday_limit_up_avg_return = Column(Numeric(6, 2))
    market_status = Column(String(20))


class MarketConfig(Base):
    __tablename__ = "market_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    param_name = Column(String(50), unique=True, nullable=False)
    param_value = Column(Numeric, nullable=False)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
