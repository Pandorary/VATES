"""用户相关模型"""
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Date, ForeignKey, func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(100), unique=True, nullable=True)
    email = Column(String(120), unique=True, nullable=True)
    nickname = Column(String(50))
    avatar_url = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_login = Column(TIMESTAMP)
    agreed_disclaimer = Column(Boolean, default=False)


class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    code = Column(String(10), primary_key=True)
    added_at = Column(TIMESTAMP, server_default=func.now())
    in_observe_pool = Column(Boolean, default=False)
