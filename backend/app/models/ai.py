"""AI 提示词模板模型"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, func
from app.database import Base


class AIPromptTemplate(Base):
    __tablename__ = "ai_prompt_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    template_content = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
