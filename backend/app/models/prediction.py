"""预测记录、复盘记录、数据快照模型"""
import uuid
from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, TIMESTAMP, func
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class PredictionRecord(Base):
    __tablename__ = "prediction_records"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    type = Column(String(10), nullable=False)  # stock / industry
    code = Column(String(10), default="")      # 股票代码（个股）
    name = Column(String(50), nullable=False)   # 标的名称
    horizon = Column(String(20), default="")    # tomorrow/week/1m/3m（个股）/ short_long（行业）
    prediction_content = Column(Text, nullable=False, default="")
    confidence_label = Column(String(10), default="")  # 高/中/低
    status = Column(String(20), default="tracking")     # tracking/reviewed_match/reviewed_deviate/expired
    is_deleted = Column(Boolean, default=False, server_default="0")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    prediction_id = Column(String(36), nullable=False, index=True)
    structured_data = Column(Text, nullable=False, default="{}")  # JSON
    source_urls = Column(Text, nullable=False, default="[]")       # JSON array
    fetch_timestamp = Column(TIMESTAMP, server_default=func.now())
    confidence_label = Column(String(10), default="")


class ReviewRecord(Base):
    __tablename__ = "review_records"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    prediction_id = Column(String(36), nullable=False, index=True)
    review_type = Column(String(20), nullable=False)  # stock_review_xxx / industry_review_short / industry_review_long
    accuracy_rating = Column(String(20), default="")   # accurate/partial/inaccurate/wrong
    deviation_reason = Column(String(20), default="")   # data_issue/logic_flaw/unforeseen
    review_content = Column(Text, nullable=False, default="")
    created_at = Column(TIMESTAMP, server_default=func.now())
