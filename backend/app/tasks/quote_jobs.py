"""定时行情采集任务"""
import logging
from app.database import async_session_factory

logger = logging.getLogger(__name__)


async def collect_quotes_job():
    """每分钟采集所有跟踪股票的行情"""
    try:
        from app.services.quotes.manager import get_quote_manager
        manager = get_quote_manager()
        async with async_session_factory() as db:
            count = await manager.refresh_all_tracked(db)
            await db.commit()
            logger.info(f"定时行情采集: {count} 只股票已更新")
    except Exception as e:
        logger.error(f"定时行情采集失败: {e}")
