"""APScheduler 调度器管理"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def start_scheduler():
    """启动调度器"""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()

    # 行情采集：每1分钟
    from app.tasks.quote_jobs import collect_quotes_job
    _scheduler.add_job(
        collect_quotes_job,
        trigger=IntervalTrigger(minutes=1),
        id="collect_quotes",
        replace_existing=True,
    )

    # 新闻采集：每5分钟
    from app.tasks.news_jobs import collect_news_job
    _scheduler.add_job(
        collect_news_job,
        trigger=IntervalTrigger(minutes=5),
        id="collect_news",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("APScheduler 调度器已启动 (行情: 每1分钟, 新闻: 每5分钟)")


async def stop_scheduler():
    """停止调度器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler 调度器已停止")
