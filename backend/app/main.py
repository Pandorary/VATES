"""Vates - 交易状态感知与风控辅助系统 API 入口"""
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db, get_db, engine

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库表并启动定时任务"""
    await init_db()

    # 每日 15:40 盘后数据同步 (仅交易日执行，APScheduler 自带周几过滤)
    from app.tasks.daily_jobs import run_daily_sync
    scheduler.add_job(
        run_daily_sync,
        "cron",
        hour=15, minute=40,
        day_of_week="mon-fri",
        id="daily_sync",
        name="盘后数据同步",
    )
    scheduler.start()
    logger.info("APScheduler 已启动 — 每日 15:40 (工作日) 执行盘后同步")

    # 启动时执行一次同步，确保有最新数据
    try:
        await run_daily_sync()
        logger.info("启动时数据同步完成")
    except Exception as e:
        logger.warning(f"启动时数据同步失败 (不影响服务): {e}")

    yield

    scheduler.shutdown(wait=False)
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


@app.post("/api/admin/sync-data", tags=["system"])
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    """手动触发数据同步 — 拉取行情 + 市场温度"""
    from app.tasks.daily_jobs import run_daily_sync
    results = await run_daily_sync()
    return {"status": "ok", "message": "数据同步完成", "results": results}


@app.get("/api/admin/jobs", tags=["system"])
async def list_jobs():
    """查看定时任务状态"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"status": "ok", "jobs": jobs}


# 注册路由
from app.routers.chat import router as chat_router
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
