"""持仓股模型"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, TIMESTAMP, func
from app.database import Base


class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    code = Column(String(10), nullable=False)
    name = Column(String(50), default="")
    cost_price = Column(Numeric(10, 3), nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    total_assets = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, server_default="0")
