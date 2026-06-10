"""Vates - 交易状态感知与风控辅助系统 API 入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.database import init_db, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库表 + 行情系统"""
    await init_db()
    # 初始化行情管理器
    from app.services.data_engine import init_quote_manager
    await init_quote_manager()
    # 初始化行业板块管理器
    from app.services.data_engine import init_sector_manager
    await init_sector_manager()
    # 启动定时采集
    from app.services.data_engine.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()
    yield
    await stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# 注册路由
from app.routers.chat import router as chat_router
from app.routers.holding import router as holding_router
from app.routers.search import router as search_router
from app.routers.tracking import router as tracking_router
from app.routers.prediction import router as prediction_router
from app.routers.quotes import router as quotes_router
from app.routers.news import router as news_router
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(holding_router, prefix="/api/v1", tags=["holdings"])
app.include_router(search_router, prefix="/api/v1", tags=["search"])
app.include_router(tracking_router, prefix="/api/v1", tags=["tracking"])
app.include_router(prediction_router, prefix="/api/v1", tags=["prediction"])
app.include_router(quotes_router, prefix="/api/v1", tags=["quotes"])
app.include_router(news_router, prefix="/api/v1", tags=["news"])
