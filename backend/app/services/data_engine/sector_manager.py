"""行业板块行情管理器 — TTL 缓存 + 故障转移 + 数据库持久化

三层数据源：东财 API → Playwright 爬虫 → LLM 兜底
"""
import logging
from datetime import datetime

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_engine.sector import (
    SectorData,
    SectorProvider,
    lookup_sector_code,
)
from app.services.data_engine.sector_eastmoney import EastMoneySectorProvider
from app.services.data_engine.sector_scraper import PlaywrightSectorProvider
from app.services.data_engine.sector_llm import LLMSectorProvider
from app.services.data_engine.sector_sina import SinaSectorProvider
from config import settings

logger = logging.getLogger(__name__)

# 模块级单例
_sector_manager: "SectorManager | None" = None


class SectorFailoverManager:
    """行业数据源故障转移引擎"""

    def __init__(self, providers: list[SectorProvider]):
        self.providers = providers

    async def fetch_sector(self, code: str, name: str = "") -> SectorData | None:
        """依次尝试各数据源获取板块行情

        code 为东财 BK 代码，name 为板块中文名。
        Sina/LLM 提供商按名称查找，其他按 BK 代码查找。
        """
        for provider in self.providers:
            try:
                if provider.name == "sina":
                    # Sina 提供商使用自己的代码体系，按名称查找
                    data = await provider.fetch_sector(name)
                elif provider.name == "llm":
                    # LLM 提供商需要名称
                    llm_provider: LLMSectorProvider = provider  # type: ignore
                    data = await llm_provider.fetch_sector_by_name(name)
                else:
                    data = await provider.fetch_sector(code)
                if data:
                    logger.debug(f"[{code}] {provider.name} 板块数据获取成功")
                    return data
            except Exception as e:
                logger.warning(f"[{code}] {provider.name} 板块数据获取失败: {e}")
        logger.warning(f"[{code}] 所有板块数据源均失败")
        return None


class SectorManager:
    """行业板块行情管理器：缓存 → 故障转移 → 数据库"""

    def __init__(self):
        self.cache: TTLCache[str, SectorData] = TTLCache(
            maxsize=100,
            ttl=settings.STOCK_CACHE_TTL,
        )
        providers = [
            SinaSectorProvider(),
            EastMoneySectorProvider(),
            PlaywrightSectorProvider(),
            LLMSectorProvider(),
        ]
        self.failover = SectorFailoverManager(providers)

    async def get_sector(self, name_or_code: str, db: AsyncSession | None = None) -> SectorData | None:
        """获取板块行情（按名称或代码）

        流程：名称→代码查找 → 缓存 → 故障转移 → DB 回退
        """
        # 1. 名称→代码映射
        info = await lookup_sector_code(name_or_code)
        if info:
            code = info["code"]
            sector_name = info["name"]
        else:
            # 假设输入本身就是代码
            code = name_or_code
            sector_name = name_or_code

        # 2. TTL 缓存命中
        cache_key = code
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 3. 故障转移获取
        data = await self.failover.fetch_sector(code, sector_name)
        if data:
            self.cache[cache_key] = data
            if db:
                await self._save_to_db(data, db)
            return data

        # 4. 全部失败，尝试数据库
        if db:
            db_data = await self._read_from_db(code, db)
            if db_data:
                logger.info(f"[{code}] 板块数据源全失败，使用数据库缓存")
                return db_data

        return None

    async def _save_to_db(self, data: SectorData, db: AsyncSession) -> None:
        """写入 sector_quotes 表（INSERT OR REPLACE）"""
        import json

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            text("""INSERT OR REPLACE INTO sector_quotes
                    (code, name, sector_index, sector_change_percent,
                     leading_stocks, policy_news, fund_flow, source, updated_at)
                    VALUES (:code, :name, :idx, :chg,
                            :leaders, :news, :flow, :src, :now)"""),
            {
                "code": data.code,
                "name": data.name,
                "idx": data.sector_index,
                "chg": data.sector_change_percent,
                "leaders": json.dumps(data.leading_stocks, ensure_ascii=False),
                "news": json.dumps(data.policy_news, ensure_ascii=False),
                "flow": data.fund_flow,
                "src": data.source,
                "now": now,
            },
        )
        await db.flush()

    @staticmethod
    async def _read_from_db(code: str, db: AsyncSession) -> SectorData | None:
        """从数据库读取最新板块行情"""
        import json

        row = await db.execute(
            text("""SELECT code, name, sector_index, sector_change_percent,
                           leading_stocks, policy_news, fund_flow, source
                    FROM sector_quotes WHERE code=:code"""),
            {"code": code},
        )
        r = row.fetchone()
        if not r:
            return None
        return SectorData(
            code=r[0] or "",
            name=r[1] or "",
            sector_index=r[2],
            sector_change_percent=r[3],
            leading_stocks=json.loads(r[4]) if r[4] else [],
            policy_news=json.loads(r[5]) if r[5] else [],
            fund_flow=r[6] or "",
            source=r[7] or "",
        )


async def init_sector_manager() -> SectorManager:
    """初始化行业板块管理器单例"""
    global _sector_manager
    if _sector_manager is None:
        _sector_manager = SectorManager()
        logger.info("行业板块管理器初始化完成")
    return _sector_manager


def get_sector_manager() -> SectorManager:
    """获取行业板块管理器单例"""
    if _sector_manager is None:
        raise RuntimeError("行业板块管理器未初始化，请先调用 init_sector_manager()")
    return _sector_manager


async def get_sector(name_or_code: str, db: AsyncSession | None = None) -> SectorData | None:
    """便捷函数：获取板块行情"""
    return await get_sector_manager().get_sector(name_or_code, db)
