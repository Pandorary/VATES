"""智能数据引擎 — 基于 data_engine 系统的数据提取

行情数据统一通过 app.services.data_engine 包获取（多源故障转移 + TTL 缓存 + 定时采集）。
本模块负责：
- 将 QuoteData 转换为预测系统所需的结构化格式
- 行业数据获取（三层数据源：东财 API → Playwright 爬虫 → LLM 兜底）
- AI 模板查询
"""
import json
import logging
import re
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------- 个股数据获取（基于 data_engine 系统）----------


async def _name_to_code(name: str, db: AsyncSession) -> str | None:
    """按股票名称查找代码（数据库 → 外部 API 兜底）"""
    # 1. 先查数据库
    for table in ("stocks", "stock_quotes"):
        row = await db.execute(
            text(f"SELECT code FROM {table} WHERE name=:name LIMIT 1"),
            {"name": name},
        )
        r = row.fetchone()
        if r and r[0]:
            return r[0]

    # 2. 数据库没有，通过东方财富搜索 API 查找
    from app.services.data_engine.eastmoney import search_stock_by_name

    result = await search_stock_by_name(name)
    if result:
        logger.info(f"外部搜索找到: {name} → {result['code']}")
        return result["code"]

    return None


async def fetch_stock_data(code: str, name: str, db: AsyncSession) -> dict:
    """基于数据引擎获取个股行情 + 新闻，返回结构化数据+置信度

    行情数据来自 data_engine 包（多源故障转移 + TTL 缓存 + DB 回退），
    新闻数据来自 news 表（定时采集）。
    """
    from app.services.data_engine import get_quote

    structured: dict = {}
    source_urls: list[str] = []

    # 1. 从 quotes 系统获取行情（缓存 → 故障转移 → DB 回退）
    quote = await get_quote(code, db)

    # 如果 code 不像股票代码（非6位数字），尝试按名称反查
    if not quote and not re.fullmatch(r"\d{6}", code):
        real_code = await _name_to_code(code, db)
        if real_code:
            logger.info(f"名称→代码: {code} → {real_code}")
            quote = await get_quote(real_code, db)

    if quote:
        structured = {
            "name": quote.name or name,
            "latest_price": quote.price,
            "latest_close_price": quote.close,
            "open_price": quote.open,
            "high_price": quote.high,
            "low_price": quote.low,
            "price_change_percent": quote.change_percent,
            "change": quote.change,
            "volume": quote.volume,
            "amount": quote.amount,
            "trade_date": datetime.now().strftime("%Y-%m-%d"),
        }
        source_urls.append(f"{code}:{quote.source}")
        confidence = "中"
    else:
        confidence = "低"

    # 2. 获取近期新闻作为 key_events
    try:
        key_events = await _get_stock_events(code, db)
        structured["key_events"] = key_events if key_events else []
    except Exception as e:
        logger.warning(f"新闻获取失败 [{code}]: {e}")
        structured["key_events"] = []

    return {
        "structured_data": structured,
        "confidence_label": confidence,
        "source_urls": source_urls,
        "fetch_timestamp": datetime.now().isoformat(),
    }


async def _get_stock_events(code: str, db: AsyncSession) -> list[str]:
    """从 news 表获取指定股票的近期新闻标题"""
    rows = await db.execute(
        text("""
            SELECT title FROM news
            WHERE code = :code
            ORDER BY publish_time DESC
            LIMIT 5
        """),
        {"code": code},
    )
    return [r[0] for r in rows.fetchall() if r[0]]


# ---------- 行业数据获取 ----------

# 置信度映射：数据源 → 默认置信度
_SECTOR_CONFIDENCE = {"sina": "高", "eastmoney": "高", "playwright": "中", "llm": "低"}


def _assess_llm_confidence(sector) -> str:
    """评估 LLM 数据完整性，数据足够时提升到 '中'"""
    complete_count = sum(1 for v in [
        sector.sector_index,
        sector.sector_change_percent,
        sector.leading_stocks,
        sector.fund_flow,
    ] if v not in (None, "", []))
    return "中" if complete_count >= 3 else "低"


async def fetch_industry_data(name: str, db: AsyncSession) -> dict:
    """三层数据源获取行业数据：东财 API → Playwright 爬虫 → LLM 兜底

    行情数据来自 sector 数据引擎（多源故障转移 + TTL 缓存 + DB 回退）。
    """
    from app.services.data_engine.sector_manager import get_sector

    # 1. 三层数据源获取行情
    sector = await get_sector(name, db)

    if not sector:
        return {
            "structured_data": {},
            "confidence_label": "低",
            "source_urls": [],
            "fetch_timestamp": datetime.now().isoformat(),
        }

    # 2. 置信度评估（LLM 源检查数据完整性）
    if sector.source == "llm":
        confidence = _assess_llm_confidence(sector)
    else:
        confidence = _SECTOR_CONFIDENCE.get(sector.source, "低")

    # 3. 没有政策新闻时，从 news 表补充（所有数据源都需要）
    if not sector.policy_news:
        sector.policy_news = await _get_sector_news(sector.name, db)

    # 4. 组装返回
    structured = {
        "name": sector.name or name,
        "code": sector.code,
        "sector_index": sector.sector_index,
        "sector_change_percent": sector.sector_change_percent,
        "leading_stocks": sector.leading_stocks,
        "policy_news": sector.policy_news,
        "fund_flow": sector.fund_flow,
        "trade_date": datetime.now().strftime("%Y-%m-%d"),
    }

    return {
        "structured_data": {k: v for k, v in structured.items() if v not in (None, "", [])},
        "confidence_label": confidence,
        "source_urls": [f"{sector.code}:{sector.source}"],
        "fetch_timestamp": datetime.now().isoformat(),
    }


async def _get_sector_news(sector_name: str, db: AsyncSession) -> list[str]:
    """从 news 表获取相关行业新闻标题"""
    try:
        rows = await db.execute(
            text("""
                SELECT title FROM news
                WHERE title LIKE :kw OR content_preview LIKE :kw
                ORDER BY publish_time DESC LIMIT 5
            """),
            {"kw": f"%{sector_name}%"},
        )
        return [r[0] for r in rows.fetchall() if r[0]]
    except Exception as e:
        logger.debug(f"行业新闻查询失败 [{sector_name}]: {e}")
        return []


# ---------- 辅助函数 ----------

def _parse_json_from_llm(raw: str) -> dict | None:
    """从 LLM 响应中解析 JSON"""
    if not raw:
        return None

    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
    extract = json_match.group(1) if json_match else raw

    try:
        return json.loads(extract)
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        brace_match = re.search(r"\{[\s\S]*\}", extract)
        if brace_match:
            return json.loads(brace_match.group())
    except (json.JSONDecodeError, ValueError):
        pass

    return None


# ---------- 获取场景激活模板 ----------

async def get_active_template(db: AsyncSession, scene: str) -> str | None:
    """获取指定场景的激活模板"""
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE scene=:scene AND is_active=1 AND is_deleted=0 LIMIT 1"),
        {"scene": scene},
    )
    r = row.fetchone()
    return r[0] if r else None
