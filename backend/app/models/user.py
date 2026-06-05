"""用户相关模型"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func
from app.database import Base


class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    user_id = Column(Integer, primary_key=True)
    code = Column(String(10), primary_key=True)
    added_at = Column(TIMESTAMP, server_default=func.now())
    in_observe_pool = Column(Boolean, default=False)
