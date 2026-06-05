"""AI Chat 缓存模型 - 同一天同一只股票只调一次 LLM"""
import uuid
from sqlalchemy import Column, String, Text, Date, TIMESTAMP, func
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AIChatCache(Base):
    __tablename__ = "ai_chat_cache"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query = Column(String(50), nullable=False, index=True)
    response = Column(Text, nullable=False, default="")
    search_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class PredictionCache(Base):
    """预测结果缓存 — tracking.py 通过原始 SQL 读写，ORM 仅用于 DDL 建表"""
    __tablename__ = "prediction_cache"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query = Column(String(50), nullable=False, index=True)
    horizon = Column(String(20), nullable=False)
    response = Column(Text, nullable=False, default="")
    search_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
