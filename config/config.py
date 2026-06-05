"""应用配置管理"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # 应用基础
    APP_NAME: str = "Vates"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库 - 开发模式默认 SQLite，路径相对于项目根目录
    DATABASE_URL: str = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'db' / 'vates.db'}"

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    # LLM
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_MAX_TOKENS: int = 8192
    LLM_TEMPERATURE: float = 0.3

    # 行情数据采集
    STOCK_CACHE_TTL: int = 60           # 缓存过期秒数
    STOCK_CACHE_MAX_SIZE: int = 200     # 最大缓存条目
    STOCK_DEFAULT_CODES: str = ""       # 默认股票代码，逗号分隔
    STOCK_TRADING_HOURS_ONLY: bool = True  # 仅交易时段采集

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
