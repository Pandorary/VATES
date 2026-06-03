"""东方财富行情适配器 — 次数据源"""
import logging

import httpx

from app.services.quotes.base import QuoteData, QuoteProvider, _market_prefix

logger = logging.getLogger(__name__)


class EastMoneyProvider(QuoteProvider):
    name = "eastmoney"

    # f43=最新价 f44=最高 f45=最低 f46=开盘 f47=成交量 f48=成交额
    # f50=量比 f51=涨停价 f52=跌停价 f55=换手率 f57=代码 f58=名称 f170=涨跌幅
    FIELDS = "f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f170"

    async def fetch_quote(self, code: str) -> QuoteData | None:
        market, _ = _market_prefix(code)
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/get"
                f"?secid={market}.{code}&fields={self.FIELDS}"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                data = resp.json().get("data")
                if not data:
                    return None
                return self._parse(data)
        except Exception as e:
            logger.warning(f"东方财富行情获取失败 [{code}]: {e}")
            return None

    @staticmethod
    def _parse(data: dict) -> QuoteData | None:
        try:
            code = str(data.get("f57", ""))
            name = str(data.get("f58", ""))
            price = data.get("f43")
            high = data.get("f44")
            low = data.get("f45")
            open_price = data.get("f46")
            volume = data.get("f47")  # 手
            amount = data.get("f48")  # 元
            change_pct = data.get("f170")

            # 东方财富返回的数值可能是整数（分单位），需要除以1000
            # f43 等价格字段: 实际值 = 原值 / 1000 (对于部分字段)
            # 但实际上东方财富 push2 API 返回的就是正常价格，不需要除
            # 只有在数据异常（如价格>100000）时才做转换
            def safe_float(v) -> float | None:
                if v is None or v == "-":
                    return None
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return None

            price_val = safe_float(price)
            # 如果价格看起来异常大（>100000），可能是以分为单位
            if price_val and price_val > 100000:
                price_val = price_val / 1000

            return QuoteData(
                code=code,
                name=name,
                price=price_val,
                open=safe_float(open_price),
                high=safe_float(high),
                low=safe_float(low),
                close=None,  # 东方财富此接口不直接返回昨收
                change=None,  # 可通过 price - close 计算
                change_percent=safe_float(change_pct),
                volume=safe_float(volume),
                amount=safe_float(amount),
                source="eastmoney",
            )
        except Exception as e:
            logger.warning(f"东方财富行情解析失败: {e}")
            return None
