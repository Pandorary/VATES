"""行业分析缓存模型 - 同天同一行业只调一次 LLM"""
import uuid
from sqlalchemy import Column, String, Text, Date, TIMESTAMP, func
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class IndustryAnalysisCache(Base):
    __tablename__ = "industry_analysis_cache"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    query = Column(String(50), nullable=False, index=True)
    response = Column(Text, nullable=False, default="")
    search_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
