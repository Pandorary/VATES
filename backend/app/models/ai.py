"""AI 提示词模板模型"""
import uuid
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, func
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AIPromptTemplate(Base):
    __tablename__ = "ai_prompts"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    scene = Column(String(50), nullable=False, default="", index=True)
    role = Column(String(50), default="")
    role_name = Column(String(100), nullable=False)
    module = Column(String(50), default="")
    skill = Column(String(50), default="")
    skill_summary = Column(String(50), default="")
    skill_detail = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    created_by = Column(String(50), default="")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50), default="")
    is_deleted = Column(Boolean, default=False, server_default="0")


class AICallLog(Base):
    __tablename__ = "ai_call_logs"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    template_id = Column(String(36), nullable=True)
    scene = Column(String(50), nullable=False, default="")
    input_summary = Column(String(200), default="")
    output_summary = Column(String(200), default="")
    confidence_label = Column(String(10), default="")
    created_at = Column(TIMESTAMP, server_default=func.now())
