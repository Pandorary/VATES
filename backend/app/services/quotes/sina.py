"""新浪财经行情适配器 — 第三数据源"""
import logging

import httpx

from app.services.quotes.base import QuoteData, QuoteProvider, _market_prefix

logger = logging.getLogger(__name__)


class SinaProvider(QuoteProvider):
    name = "sina"

    async def fetch_quote(self, code: str) -> QuoteData | None:
        _, prefix = _market_prefix(code)
        try:
            url = f"https://hq.sinajs.cn/list={prefix}{code}"
            headers = {"Referer": "https://finance.sina.com.cn"}
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                return self._parse(resp.text, code)
        except Exception as e:
            logger.warning(f"新浪行情获取失败 [{code}]: {e}")
            return None

    @staticmethod
    def _parse(raw: str, code: str) -> QuoteData | None:
        """解析新浪行情响应: var hq_str_sh600519="名称,开,昨收,当前价,高,低,...";"""
        try:
            # 提取引号内的内容
            if '="' not in raw:
                return None
            value = raw.split('="', 1)[1].rstrip('"; \n')
            if not value:
                return None

            fields = value.split(",")
            if len(fields) < 32:
                return None

            # 新浪行情字段顺序:
            # [0]名称 [1]开盘 [2]昨收 [3]当前价 [4]最高 [5]最低
            # [6]买一 [7]卖一 [8]成交量(股) [9]成交额(元)
            name = fields[0]
            open_price = float(fields[1]) if fields[1] else None
            prev_close = float(fields[2]) if fields[2] else None
            current_price = float(fields[3]) if fields[3] else None
            high = float(fields[4]) if fields[4] else None
            low = float(fields[5]) if fields[5] else None
            volume_shares = float(fields[8]) if fields[8] else None  # 股
            amount = float(fields[9]) if fields[9] else None  # 元

            # 计算涨跌
            change = None
            change_pct = None
            if current_price and prev_close and prev_close > 0:
                change = round(current_price - prev_close, 3)
                change_pct = round(change / prev_close * 100, 2)

            return QuoteData(
                code=code,
                name=name,
                price=current_price,
                open=open_price,
                high=high,
                low=low,
                close=prev_close,
                change=change,
                change_percent=change_pct,
                volume=volume_shares / 100 if volume_shares else None,  # 股→手
                amount=amount,
                source="sina",
            )
        except (ValueError, IndexError) as e:
            logger.debug(f"新浪行情解析失败: {e}, raw={raw[:80]}")
            return None
