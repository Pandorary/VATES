"""应用配置管理"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用基础
    APP_NAME: str = "Vates"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库 - 开发模式默认 SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./vates_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "vates-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    # 数据抓取
    AKSHARE_RETRY_COUNT: int = 3
    AKSHARE_RETRY_DELAY: int = 10

    # 交易日15:40抓取
    DATA_FETCH_HOUR: int = 15
    DATA_FETCH_MINUTE: int = 40

    # 模式扫描
    SCAN_HOUR: int = 16
    SCAN_MINUTE: int = 45

    # 复盘生成
    REVIEW_HOUR: int = 17
    REVIEW_MINUTE: int = 10

    # LLM
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
