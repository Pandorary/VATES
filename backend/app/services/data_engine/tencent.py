"""腾讯财经行情适配器 — 主数据源，支持批量查询"""
import logging

import httpx

from app.services.data_engine.base import QuoteData, QuoteProvider, _market_prefix

logger = logging.getLogger(__name__)


class TencentProvider(QuoteProvider):
    name = "tencent"

    async def fetch_quote(self, code: str) -> QuoteData | None:
        _, prefix = _market_prefix(code)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"https://qt.gtimg.cn/q={prefix}{code}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                return self._parse(resp.text, code)
        except Exception as e:
            logger.warning(f"腾讯行情获取失败 [{code}]: {e}")
            return None

    async def fetch_quotes_batch(self, codes: list[str]) -> dict[str, QuoteData]:
        """批量获取，腾讯支持逗号分隔多只股票（最多约20只）"""
        results: dict[str, QuoteData] = {}
        # 分批，每批20只
        for i in range(0, len(codes), 20):
            batch = codes[i:i + 20]
            params = ",".join(f"{_market_prefix(c)[1]}{c}" for c in batch)
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    url = f"https://qt.gtimg.cn/q={params}"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    for line in resp.text.split(";"):
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        quote = self._parse_line(line)
                        if quote:
                            results[quote.code] = quote
            except Exception as e:
                logger.warning(f"腾讯批量行情获取失败: {e}")
        return results

    @staticmethod
    def _parse(raw: str, fallback_code: str) -> QuoteData | None:
        """解析整个响应文本，取第一只股票"""
        for line in raw.split(";"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            quote = TencentProvider._parse_line(line)
            if quote:
                return quote
        return None

    @staticmethod
    def _parse_line(line: str) -> QuoteData | None:
        """解析单行: v_sh600519="1~贵州茅台~600519~当前价~..." """
        try:
            eq_pos = line.index("=")
            value_part = line[eq_pos + 1:].strip().strip('"')
            if not value_part:
                return None
            fields = value_part.split("~")
            if len(fields) < 35:
                return None
            # 关键字段位置（腾讯行情字段索引，0-based）
            # [0] 市场代码, [1] 名称, [2] 代码, [3] 当前价, [4] 昨收,
            # [5] 今开, [6] 成交量(手), [7] 外盘, [8] 内盘,
            # [30] 日期时间, [31] 涨跌额, [32] 涨跌幅%,
            # [33] 最高, [34] 最低, [37] 成交额(万)

            name = fields[1]
            code = fields[2]
            price = float(fields[3]) if fields[3] else None
            prev_close = float(fields[4]) if fields[4] else None
            open_price = float(fields[5]) if fields[5] else None
            volume = float(fields[6]) if fields[6] else None
            change = float(fields[31]) if fields[31] else None
            change_pct = float(fields[32]) if fields[32] else None
            amount_wan = float(fields[37]) if fields[37] else None  # 万元

            high = float(fields[33]) if fields[33] else None
            low = float(fields[34]) if fields[34] else None

            return QuoteData(
                code=code,
                name=name,
                price=price,
                open=open_price,
                high=high,
                low=low,
                close=prev_close,
                change=change,
                change_percent=change_pct,
                volume=volume,
                amount=amount_wan * 10000 if amount_wan else None,  # 万→元
                source="tencent",
            )
        except (ValueError, IndexError) as e:
            logger.debug(f"腾讯行情解析失败: {e}, line={line[:80]}")
            return None
