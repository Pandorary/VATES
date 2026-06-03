"""预测跟踪模型 — 记录用户加入跟踪的个股/行业"""
from sqlalchemy import Column, String, Boolean, TIMESTAMP, Integer, func
from app.database import Base


class PredictionTracking(Base):
    __tablename__ = "prediction_tracking"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(10), nullable=False)    # stock / industry
    name = Column(String(50), nullable=False)    # 标准化名称
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
