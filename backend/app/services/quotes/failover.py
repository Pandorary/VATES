"""多源故障转移引擎 — 按优先级依次尝试数据源"""
import logging

from app.services.quotes.base import QuoteData, QuoteProvider

logger = logging.getLogger(__name__)


class FailoverManager:
    """按优先级调用多个数据源适配器，返回第一个成功的结果"""

    def __init__(self, providers: list[QuoteProvider]):
        self.providers = providers

    async def get_quote(self, code: str) -> QuoteData | None:
        """依次尝试各数据源获取单只股票行情"""
        for provider in self.providers:
            try:
                quote = await provider.fetch_quote(code)
                if quote:
                    logger.debug(f"[{code}] {provider.name} 获取成功")
                    return quote
            except Exception as e:
                logger.warning(f"[{code}] {provider.name} 获取失败: {e}")
        logger.warning(f"[{code}] 所有数据源均失败")
        return None

    async def get_quotes_batch(self, codes: list[str]) -> dict[str, QuoteData]:
        """批量获取行情，优先使用支持批量的主数据源，失败后逐个回退"""
        results: dict[str, QuoteData] = {}
        remaining = list(codes)

        # 第一轮：用主数据源（腾讯）批量获取
        if remaining and self.providers:
            try:
                batch = await self.providers[0].fetch_quotes_batch(remaining)
                results.update(batch)
                remaining = [c for c in remaining if c not in results]
                if batch:
                    logger.debug(f"批量获取: {len(batch)} 只成功 (主数据源 {self.providers[0].name})")
            except Exception as e:
                logger.warning(f"批量获取失败: {e}")

        # 第二轮：逐个用各数据源获取失败的股票
        for code in remaining:
            quote = await self.get_quote(code)
            if quote:
                results[code] = quote

        return results
