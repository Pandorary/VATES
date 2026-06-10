"""东方财富行业数据适配器 — 主数据源

三路 API：
1. 板块详情 — push2/qt/stock/get?secid=90.{code}
2. 领涨个股 — push2/qt/clist/get?fs=b:{code} 取涨幅前5
3. 资金流向 — push2/qt/stock/fflow/kline/get?secid=90.{code} 取最近1日
"""
import logging

import httpx

from app.services.data_engine.sector import SectorData, SectorProvider

logger = logging.getLogger(__name__)


class EastMoneySectorProvider(SectorProvider):
    name = "eastmoney"

    # 板块详情字段
    # f43=最新价(点位) f44=最高 f45=最低 f46=开盘 f47=成交量 f48=成交额
    # f57=代码 f58=名称 f170=涨跌幅 f62=主力净流入 f184=主力净流入占比
    DETAIL_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f170,f62,f184"

    # 成分股字段
    MEMBER_FIELDS = "f2,f3,f12,f14,f20"

    async def fetch_sector(self, code: str) -> SectorData | None:
        try:
            # 1. 板块详情
            detail = await self._fetch_detail(code)
            if not detail:
                return None

            # 2. 领涨个股（并发）
            leaders = await self._fetch_leaders(code)

            # 3. 资金流向
            fund_flow = await self._fetch_fund_flow(code)

            return SectorData(
                code=detail.get("code", code),
                name=detail.get("name", ""),
                sector_index=detail.get("index_val"),
                sector_change_percent=detail.get("change_pct"),
                leading_stocks=leaders,
                policy_news=[],
                fund_flow=fund_flow,
                source="eastmoney",
            )
        except Exception as e:
            logger.warning(f"东方财富板块数据获取失败 [{code}]: {e}")
            return None

    async def _fetch_detail(self, code: str) -> dict | None:
        """获取板块指数点位和涨跌幅"""
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/get"
                f"?secid=90.{code}&fields={self.DETAIL_FIELDS}"
            )
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                data = resp.json().get("data")
                if not data:
                    return None

                return {
                    "code": str(data.get("f57", code)),
                    "name": str(data.get("f58", "")),
                    "index_val": _safe_float(data.get("f43")),
                    "change_pct": _safe_float(data.get("f170")),
                }
        except Exception as e:
            logger.debug(f"板块详情获取失败 [{code}]: {e}")
            return None

    async def _fetch_leaders(self, code: str) -> list[dict]:
        """获取板块领涨个股（按涨幅降序，最多5只）"""
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/clist/get"
                f"?fs=b:{code}"
                "&fid=f3&po=0&pn=5"
                f"&fields={self.MEMBER_FIELDS}"
            )
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json().get("data")
                if not data or not data.get("diff"):
                    return []

                leaders = []
                for item in data["diff"]:
                    leaders.append({
                        "code": str(item.get("f12", "")),
                        "name": str(item.get("f14", "")),
                        "change_pct": _safe_float(item.get("f3")),
                    })
                return leaders
        except Exception as e:
            logger.debug(f"板块领涨股获取失败 [{code}]: {e}")
            return []

    async def _fetch_fund_flow(self, code: str) -> str:
        """获取板块资金流向概况"""
        try:
            url = (
                f"https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
                f"?secid=90.{code}"
                "&fields1=f1,f2,f3"
                "&fields2=f51,f52,f53"
            )
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return ""
                data = resp.json().get("data")
                if not data or not data.get("klines"):
                    return ""

                # 取最近一条 kline: "日期,主力净流入,小单净流入,中单净流入,大单净流入,超大单净流入"
                latest = data["klines"][-1]
                parts = latest.split(",")
                if len(parts) >= 2:
                    flow_val = _safe_float(parts[1])  # 主力净流入（万元）
                    if flow_val is not None:
                        if flow_val > 0:
                            return f"主力净流入 {_fmt_amount(flow_val)}"
                        elif flow_val < 0:
                            return f"主力净流出 {_fmt_amount(abs(flow_val))}"
                        else:
                            return "主力资金无明显流入流出"
                return ""
        except Exception as e:
            logger.debug(f"板块资金流向获取失败 [{code}]: {e}")
            return ""


def _safe_float(v) -> float | None:
    """安全转 float"""
    if v is None or v == "-" or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _fmt_amount(val: float) -> str:
    """格式化金额（万元）"""
    if val >= 10000:
        return f"{val / 10000:.2f}亿"
    return f"{val:.0f}万"
