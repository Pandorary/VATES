"""腾讯财经行情适配器 — 主数据源，支持批量查询"""
import logging

import httpx

from app.services.quotes.base import QuoteData, QuoteProvider, _market_prefix

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
            # 关键字段位置（腾讯行情字段索引）
            # [1] 市场, [2] 名称, [3] 代码, [4] 当前价, [5] 昨收,
            # [6] 今开, [7] 成交量(手), [8] 外盘, [9] 内盘,
            # [30] 最高, [31] 最低(注意: 31不是最低, 需要重新确认)
            # [32] 涨跌, [33] 涨跌幅, [34] 成交额(万), [37] 换手率
            # 实际字段：[0]=市场代码 [1]=市场名 [2]=名称 [3]=代码
            # [4]=当前价 [5]=昨收 [6]=今开 [7]=成交量(手) [8]=外盘
            # [9]=内盘 [10]=买一价 ... [20]=买一量 ... [30]=涨停价
            # [31]=跌停价 [32]=涨跌 [33]=涨跌幅 [34]=成交额(万)

            name = fields[2]
            code = fields[3]
            price = float(fields[4]) if fields[4] else None
            prev_close = float(fields[5]) if fields[5] else None
            open_price = float(fields[6]) if fields[6] else None
            volume = float(fields[7]) if fields[7] else None
            change = float(fields[32]) if fields[32] else None
            change_pct = float(fields[33]) if fields[33] else None
            amount_wan = float(fields[34]) if fields[34] else None  # 万元

            # 最高/最低需要从字段 [33] 或 [41][42] 获取，不同接口略有差异
            # 腾讯接口: [33] 涨跌幅, [34] 成交额
            # 高低价可能在 买卖盘之间，此处尝试从已知位置获取
            high = None
            low = None
            # 部分版本 [41]=最高 [42]=最低
            if len(fields) > 42:
                high = float(fields[41]) if fields[41] else None
                low = float(fields[42]) if fields[42] else None

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
