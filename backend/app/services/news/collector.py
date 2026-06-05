"""新闻采集器 — 东方财富个股新闻 + 新浪财经宏观新闻"""
import logging
from datetime import datetime

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_engine.base import _market_prefix

logger = logging.getLogger(__name__)

# 宏观新闻源
MACRO_NEWS_URL = (
    "https://feed.mix.sina.com.cn/api/roll/get"
    "?pageid=153&lid=2512&num=15"  # 新浪财经要闻
)

# 行业板块新闻源
SECTOR_NEWS_URL = (
    "https://feed.mix.sina.com.cn/api/roll/get"
    "?pageid=153&lid=2515&num=10"  # 新浪行业研究
)


class NewsCollector:
    """新闻采集器 — 个股新闻 + 宏观新闻"""

    @staticmethod
    async def collect_stock_news(code: str) -> list[dict]:
        """获取单只个股新闻（东方财富 push2 API）"""
        market, _ = _market_prefix(code)
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/news/get"
                f"?secid={market}.{code}&page=1&size=10"
            )
            async with httpx.AsyncClient(timeout=10, headers={
                "Referer": "https://quote.eastmoney.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"东方财富新闻获取失败 [{code}]: HTTP {resp.status_code}")
                    return []
                data = resp.json()
        except Exception as e:
            logger.warning(f"东方财富新闻获取异常 [{code}]: {e}")
            return []

        items = []
        raw_items = data.get("data", {}).get("items", []) or []
        for item in raw_items:
            title = item.get("title", "")
            news_url = item.get("url", "")
            if not title:
                continue
            items.append({
                "code": code,
                "title": title,
                "url": news_url,
                "publish_time": _parse_time(item.get("show_time")),
                "source_site": "eastmoney",
                "content_preview": item.get("digest", "")[:500],
            })
        return items

    @staticmethod
    async def collect_macro_news() -> list[dict]:
        """获取宏观/板块新闻（新浪财经 roll API）"""
        all_items: list[dict] = []

        for label, url in [("macro", MACRO_NEWS_URL), ("sector", SECTOR_NEWS_URL)]:
            try:
                async with httpx.AsyncClient(timeout=10, headers={
                    "Referer": "https://finance.sina.com.cn/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"新浪{label}新闻获取失败: HTTP {resp.status_code}")
                        continue
                    data = resp.json()
            except Exception as e:
                logger.warning(f"新浪{label}新闻获取异常: {e}")
                continue

            raw_list = data.get("result", {}).get("data", []) or []
            for item in raw_list:
                title = item.get("title", "")
                news_url = item.get("url", "")
                if not title:
                    continue
                all_items.append({
                    "code": None,  # 宏观新闻无个股代码
                    "title": title,
                    "url": news_url,
                    "publish_time": _parse_time(item.get("ctime")),
                    "source_site": "sina",
                    "content_preview": item.get("intro", "")[:500] or item.get("summary", "")[:500],
                })

        return all_items

    @staticmethod
    async def save_news(items: list[dict], db: AsyncSession) -> int:
        """批量保存新闻，按 title+url 去重（INSERT OR IGNORE）"""
        if not items:
            return 0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = 0
        for item in items:
            try:
                result = await db.execute(
                    text("""
                        INSERT OR IGNORE INTO news
                        (code, title, url, publish_time, source_site, content_preview, created_at)
                        VALUES (:code, :title, :url, :pub, :src, :preview, :now)
                    """),
                    {
                        "code": item["code"],
                        "title": item["title"],
                        "url": item["url"],
                        "pub": item["publish_time"],
                        "src": item["source_site"],
                        "preview": item["content_preview"],
                        "now": now,
                    },
                )
                if result.rowcount and result.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.debug(f"新闻保存跳过: {e}")

        await db.flush()
        return saved

    @staticmethod
    async def collect_and_save_all(codes: list[str], db: AsyncSession) -> int:
        """采集所有跟踪股票的个股新闻 + 宏观新闻，并写入数据库"""
        total = 0

        # 1. 宏观新闻
        logger.info("开始采集宏观新闻...")
        macro_items = await NewsCollector.collect_macro_news()
        macro_saved = await NewsCollector.save_news(macro_items, db)
        logger.info(f"宏观新闻: 获取 {len(macro_items)} 条, 新增 {macro_saved} 条")
        total += macro_saved

        # 2. 个股新闻（逐只采集）
        for code in codes:
            stock_items = await NewsCollector.collect_stock_news(code)
            if stock_items:
                saved = await NewsCollector.save_news(stock_items, db)
                if saved:
                    total += saved
                logger.debug(f"[{code}] 个股新闻: 获取 {len(stock_items)} 条, 新增 {saved} 条")

        return total


def _parse_time(val) -> str | None:
    """解析各种时间格式为 SQLite TIMESTAMP 字符串"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")

    val = str(val).strip()
    if not val:
        return None

    # 纯数字时间戳（秒或毫秒）
    if val.isdigit():
        try:
            ts = int(val)
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return None

    # 常见字符串格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return None
