"""定时新闻采集任务"""
import logging

from app.database import async_session_factory

logger = logging.getLogger(__name__)


async def collect_news_job():
    """每5分钟采集所有跟踪股票的资讯"""
    try:
        from app.services.news import NewsCollector
        from app.services.data_engine.manager import QuoteManager

        async with async_session_factory() as db:
            codes = await QuoteManager._get_tracked_codes(db)
            if not codes:
                logger.debug("无跟踪股票，跳过新闻采集")
                return

            saved = await NewsCollector.collect_and_save_all(codes, db)
            await db.commit()
            logger.info(f"定时新闻采集完成: 新增 {saved} 条")
    except Exception as e:
        logger.error(f"定时新闻采集失败: {e}")
