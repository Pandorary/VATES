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


class DeepAnalysisCache(Base):
    __tablename__ = "deep_analysis_cache"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query = Column(String(50), nullable=False, index=True)
    section = Column(String(50), nullable=False)
    response = Column(Text, nullable=False, default="")
    search_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class PredictionCache(Base):
    __tablename__ = "prediction_cache"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query = Column(String(50), nullable=False, index=True)
    horizon = Column(String(20), nullable=False)  # tomorrow / week / 1-3m / 3m+
    response = Column(Text, nullable=False, default="")
    search_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
