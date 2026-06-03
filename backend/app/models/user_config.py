"""用户配置模型"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, UniqueConstraint, func
from app.database import Base


class UserConfig(Base):
    __tablename__ = "user_config"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_config_key"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    key = Column(String(50), nullable=False)
    value = Column(String(500), nullable=False, default="")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
