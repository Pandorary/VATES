"""行情管理器 — TTL 缓存 + 故障转移 + 数据库持久化"""
import logging
from datetime import datetime

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_engine.base import QuoteData, _market_prefix
from app.services.data_engine.failover import FailoverManager
from app.services.data_engine.tencent import TencentProvider
from app.services.data_engine.eastmoney import EastMoneyProvider
from app.services.data_engine.sina import SinaProvider
from config import settings

logger = logging.getLogger(__name__)

# 模块级单例
_quote_manager: "QuoteManager | None" = None


class QuoteManager:
    """行情数据管理器：缓存 → 故障转移 → 交叉验证 → 数据库"""

    def __init__(self):
        self.cache: TTLCache[str, QuoteData] = TTLCache(
            maxsize=settings.STOCK_CACHE_MAX_SIZE,
            ttl=settings.STOCK_CACHE_TTL,
        )
        providers = [TencentProvider(), EastMoneyProvider(), SinaProvider()]
        self.failover = FailoverManager(providers)

    async def get_quote(self, code: str, db: AsyncSession | None = None) -> QuoteData | None:
        """获取单只股票行情（缓存 → 故障转移 → DB 回退）"""
        # 1. TTL 缓存命中
        if code in self.cache:
            return self.cache[code]

        # 2. 故障转移获取
        quote = await self.failover.get_quote(code)
        if quote:
            self.cache[code] = quote
            if db:
                await self._save_to_db(quote, db)
            return quote

        # 3. 全部失败，尝试从数据库读取最新记录
        if db:
            db_quote = await self._read_from_db(code, db)
            if db_quote:
                logger.info(f"[{code}] 数据源全失败，使用数据库缓存")
                return db_quote

        return None

    async def get_quotes(self, codes: list[str], db: AsyncSession | None = None) -> dict[str, QuoteData]:
        """批量获取行情"""
        results: dict[str, QuoteData] = {}
        missing: list[str] = []

        # 先查缓存
        for code in codes:
            if code in self.cache:
                results[code] = self.cache[code]
            else:
                missing.append(code)

        # 批量获取缺失的
        if missing:
            fetched = await self.failover.get_quotes_batch(missing)
            for code, quote in fetched.items():
                self.cache[code] = quote
                results[code] = quote
                if db:
                    await self._save_to_db(quote, db)

            # 仍缺失的尝试从 DB 读取
            still_missing = [c for c in missing if c not in fetched]
            if still_missing and db:
                for code in still_missing:
                    db_quote = await self._read_from_db(code, db)
                    if db_quote:
                        results[code] = db_quote

        return results

    async def refresh_all_tracked(self, db: AsyncSession) -> int:
        """刷新所有跟踪股票的行情，返回成功更新的数量"""
        codes = await self._get_tracked_codes(db)
        if not codes:
            logger.debug("无跟踪股票，跳过采集")
            return 0

        # 交易时段检查
        if settings.STOCK_TRADING_HOURS_ONLY and not self._is_trading_hours():
            logger.debug("非交易时段，跳过采集")
            return 0

        # 清空缓存以强制刷新
        self.cache.clear()
        results = await self.get_quotes(codes, db)
        logger.info(f"行情采集完成: {len(results)}/{len(codes)} 只成功")
        return len(results)

    @staticmethod
    async def _save_to_db(quote: QuoteData, db: AsyncSession) -> None:
        """写入 stock_quotes 表（INSERT OR REPLACE）"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            text("""INSERT OR REPLACE INTO stock_quotes
                    (code, name, price, open, high, low, close, change, change_percent, volume, amount, source, updated_at)
                    VALUES (:code, :name, :price, :open, :high, :low, :close, :chg, :chg_pct, :vol, :amt, :src, :now)"""),
            {
                "code": quote.code,
                "name": quote.name,
                "price": quote.price,
                "open": quote.open,
                "high": quote.high,
                "low": quote.low,
                "close": quote.close,
                "chg": quote.change,
                "chg_pct": quote.change_percent,
                "vol": quote.volume,
                "amt": quote.amount,
                "src": quote.source,
                "now": now,
            },
        )
        await db.flush()

    @staticmethod
    async def _read_from_db(code: str, db: AsyncSession) -> QuoteData | None:
        """从数据库读取最新行情"""
        row = await db.execute(
            text("SELECT code, name, price, open, high, low, close, change, change_percent, volume, amount, source "
                 "FROM stock_quotes WHERE code=:code"),
            {"code": code},
        )
        r = row.fetchone()
        if not r:
            return None
        return QuoteData(
            code=r[0], name=r[1] or "", price=r[2], open=r[3], high=r[4],
            low=r[5], close=r[6], change=r[7], change_percent=r[8],
            volume=r[9], amount=r[10], source=r[11] or "",
        )

    @staticmethod
    async def _get_tracked_codes(db: AsyncSession) -> list[str]:
        """获取所有需要跟踪的股票代码（持仓 + 自选 + 配置默认）"""
        codes: set[str] = set()

        # 持仓
        rows = await db.execute(
            text("SELECT DISTINCT code FROM holdings WHERE is_deleted=0")
        )
        for r in rows.fetchall():
            codes.add(r[0])

        # 自选
        rows = await db.execute(
            text("SELECT DISTINCT code FROM user_watchlist")
        )
        for r in rows.fetchall():
            codes.add(r[0])

        # 配置默认
        if settings.STOCK_DEFAULT_CODES:
            for c in settings.STOCK_DEFAULT_CODES.split(","):
                c = c.strip()
                if c:
                    codes.add(c)

        return sorted(codes)

    @staticmethod
    def _is_trading_hours() -> bool:
        """判断当前是否在A股交易时段（工作日 9:15-15:05）"""
        now = datetime.now()
        # 周末
        if now.weekday() >= 5:
            return False
        t = now.hour * 100 + now.minute
        return 915 <= t <= 1505


async def init_quote_manager() -> QuoteManager:
    """初始化行情管理器单例"""
    global _quote_manager
    if _quote_manager is None:
        _quote_manager = QuoteManager()
        logger.info("行情管理器初始化完成")
    return _quote_manager


def get_quote_manager() -> QuoteManager:
    """获取行情管理器单例"""
    if _quote_manager is None:
        raise RuntimeError("行情管理器未初始化，请先调用 init_quote_manager()")
    return _quote_manager


async def get_quote(code: str, db: AsyncSession | None = None) -> QuoteData | None:
    """便捷函数：获取单只股票行情"""
    return await get_quote_manager().get_quote(code, db)


async def get_quotes(codes: list[str], db: AsyncSession | None = None) -> dict[str, QuoteData]:
    """便捷函数：批量获取行情"""
    return await get_quote_manager().get_quotes(codes, db)
