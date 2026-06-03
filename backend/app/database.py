"""数据库连接管理 - 开发模式 SQLite，生产模式 PostgreSQL"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # SQLite busy timeout in seconds
    },
)


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """初始化数据库表 + 种子数据"""
    import app.models.stock  # noqa: F401
    import app.models.market  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.ai  # noqa: F401
    import app.models.chat_cache  # noqa: F401
    import app.models.holding  # noqa: F401
    import app.models.industry_cache  # noqa: F401
    import app.models.tracking  # noqa: F401
    import app.models.price_cache  # noqa: F401
    import app.models.user_config  # noqa: F401
    import app.models.prediction  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
