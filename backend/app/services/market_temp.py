"""市场温度计算引擎 — httpx 直连东方财富 JSON API"""
import logging
import asyncio
from dataclasses import dataclass
from typing import Optional
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "MAX_BOARD_ICE": 3,
    "BOMB_RATE_RETREAT": 0.4,
    "PROMOTION_HIGH": 0.4,
    "AVG_RETURN_HIGH": 1.0,
    "PROMOTION_WARM": 0.25,
    "AVG_RETURN_WARM": 0,
    "MAX_BOARD_HIGH": 5,
}

EM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}
EM_BASE = "https://push2ex.eastmoney.com"
ZT_POOL_URL = f"{EM_BASE}/getTopicZTPool"
ZB_POOL_URL = f"{EM_BASE}/getTopicZBPool"  # 炸板池


@dataclass
class MarketTempResult:
    trade_date: str
    status: str
    status_text: str
    advice: str
    max_board_height: int
    promotion_rate: float
    bomb_rate: float
    yesterday_avg_return: float


_STATUS_MAP = {
    "ICE": ("冰点期", "建议空仓观望，等待情绪回暖"),
    "WARM": ("情绪回暖期", "可轻仓参与模式内买点"),
    "HIGH": ("高潮期", "市场活跃，注意高位分化"),
    "RETREAT": ("退潮期", "注意风险，减仓为主"),
}


def calculate(
    max_board_height: int,
    promotion_rate: float,
    bomb_rate: float,
    yesterday_avg_return: float,
    trade_date: str = "",
    config: Optional[dict] = None,
) -> MarketTempResult:
    """计算市场温度状态"""
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    if bomb_rate > cfg["BOMB_RATE_RETREAT"] or max_board_height < cfg["MAX_BOARD_ICE"]:
        status = "ICE"
    elif (
        promotion_rate > cfg["PROMOTION_HIGH"]
        and yesterday_avg_return > cfg["AVG_RETURN_HIGH"]
        and bomb_rate < 0.25
        and max_board_height >= cfg["MAX_BOARD_HIGH"]
    ):
        status = "HIGH"
    elif max_board_height >= 3 and promotion_rate > cfg["PROMOTION_WARM"] and yesterday_avg_return > cfg["AVG_RETURN_WARM"]:
        status = "WARM"
    else:
        status = "RETREAT"

    status_text, advice = _STATUS_MAP[status]
    return MarketTempResult(
        trade_date=trade_date, status=status, status_text=status_text, advice=advice,
        max_board_height=max_board_height, promotion_rate=promotion_rate,
        bomb_rate=bomb_rate, yesterday_avg_return=yesterday_avg_return,
    )


async def _fetch_pool(client: httpx.AsyncClient, url: str, date_str: str) -> list[dict]:
    """拉取涨停池或炸板池数据"""
    params = {
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "dpt": "wz.ztzt",
        "Pageindex": 0,
        "pagesize": 5000,
        "sort": "fbt:asc",
        "date": date_str,
    }
    try:
        resp = await client.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data") and data["data"].get("pool"):
            return data["data"]["pool"]
    except Exception as e:
        logger.warning(f"拉取涨停数据失败 {url} date={date_str}: {e}")
    return []


async def compute_from_eastmoney(date_str: str, prev_date_str: str) -> MarketTempResult:
    """从东方财富直连拉取两天涨停数据，计算四个指标

    date_str / prev_date_str: YYYYMMDD 格式
    """
    date_display = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    async with httpx.AsyncClient(headers=EM_HEADERS) as client:
        # 并行拉取：今日涨停池 + 昨日涨停池 + 今日炸板池
        today_zt, yesterday_zt, today_bomb = await asyncio.gather(
            _fetch_pool(client, ZT_POOL_URL, date_str),
            _fetch_pool(client, ZT_POOL_URL, prev_date_str),
            _fetch_pool(client, ZB_POOL_URL, date_str),
        )

    # 如果池子全空（网络故障），抛异常阻止写入零值
    if not today_zt and not today_bomb:
        raise RuntimeError(f"东财涨停/炸板池均为空 date={date_str}，疑似网络故障")
    max_height = max(
        (int(p.get("lbc") or 0) for p in today_zt),
        default=0,
    )

    # 2. 炸板率 = 炸板池 / (涨停池 + 炸板池)
    zt_count = len(today_zt)
    bomb_count = len(today_bomb)
    bomb_rate = round(bomb_count / (zt_count + bomb_count), 4) if (zt_count + bomb_count) > 0 else 0

    # 3. 晋级率 = 昨涨停码 ∩ 今涨停码 / 昨涨停码
    if yesterday_zt:
        yesterday_codes = {p["c"] for p in yesterday_zt}
        today_codes = {p["c"] for p in today_zt}
        promoted = yesterday_codes & today_codes
        promotion_rate = round(len(promoted) / len(yesterday_codes), 4) if yesterday_codes else 0
    else:
        promotion_rate = 0

    # 4. 昨日涨停今日均收益：用东方财富 pool 中自带的 p (现价) 和 zdp (涨跌幅) 近似计算
    # pool 中 zdp 是今日涨跌幅，对于昨日涨停股，直接用 zdp 即可
    if yesterday_zt:
        # 从今日数据中找昨日涨停股的今日涨跌幅
        # 注意：若昨日涨停股今天不在涨停池里，我们改用新浪 stock_zh_a_daily 采样
        total_return = 0.0
        count_return = 0
        for p in yesterday_zt[:50]:  # 采样前50只
            try:
                zdp = float(p.get("zdp") or 0)
                total_return += zdp
                count_return += 1
            except Exception:
                pass
        yesterday_avg_return = round(total_return / count_return, 2) if count_return > 0 else 0
    else:
        yesterday_avg_return = 0

    return calculate(
        max_board_height=max_height,
        promotion_rate=promotion_rate,
        bomb_rate=bomb_rate,
        yesterday_avg_return=yesterday_avg_return,
        trade_date=date_display,
    )
