"""智能数据引擎 — 基于 data_engine 系统的数据提取 + LLM 行业数据获取

行情数据统一通过 app.services.data_engine 包获取（多源故障转移 + TTL 缓存 + 定时采集）。
本模块负责：
- 将 QuoteData 转换为预测系统所需的结构化格式
- 行业数据获取（LLM + 交叉验证）
- AI 模板查询
"""
import json
import logging
import re
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import chat as llm_chat

logger = logging.getLogger(__name__)


# ---------- 行业数据提示词 ----------

DATA_EXTRACTION_PROMPT_INDUSTRY = """你是一个严格的数据提取器。你的唯一任务是从提供的原始文本中提取结构化数据。

严禁进行任何预测、分析或推断。只提取明确出现在文本中的数据。

请提取以下字段并以 JSON 格式输出：

{{
  "sector_index": "行业指数最新点位（数字）",
  "sector_change_percent": "行业指数涨跌幅%（数字）",
  "leading_stocks": ["龙头个股名称及近期表现摘要，最多3条"],
  "policy_news": ["近期行业政策与重大事件，最多5条"],
  "fund_flow": "板块资金流向概况（净流入/净流出及金额）",
  "trade_date": "数据对应的交易日期（YYYY-MM-DD）"
}}

如果某个字段在原始文本中找不到，填 null。不要编造数据。

原始数据如下：
{raw_data}
"""


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

async def fetch_industry_data(name: str, db: AsyncSession) -> dict:
    """多源抓取行业数据"""
    results = []

    raw_texts = await _fetch_industry_raw(name)
    template = await _get_extraction_template(db, "industry")

    for source_name, raw_text in raw_texts:
        if not raw_text:
            continue
        try:
            prompt = template or DATA_EXTRACTION_PROMPT_INDUSTRY
            prompt = prompt.replace("{raw_data}", raw_text[:4000])
            result = await llm_chat(
                [{"role": "system", "content": prompt}, {"role": "user", "content": f"提取行业 {name} 的数据"}],
                temperature=0.0, max_tokens=1000,
            )
            structured = _parse_json_from_llm(result.get("content", ""))
            if structured:
                structured["_source"] = source_name
                results.append(structured)
        except Exception as e:
            logger.warning(f"行业数据提取失败 [{source_name}]: {e}")

    if not results:
        fallback = await _llm_fallback_industry(name)
        return {
            "structured_data": fallback,
            "confidence_label": "低",
            "source_urls": [],
            "fetch_timestamp": datetime.now().isoformat(),
        }

    validated, confidence = cross_validate_industry(results)
    return {
        "structured_data": validated,
        "confidence_label": confidence,
        "source_urls": [],
        "fetch_timestamp": datetime.now().isoformat(),
    }


async def _fetch_industry_raw(name: str) -> list[tuple[str, str]]:
    """获取行业原始数据（MVP 使用 LLM）"""
    try:
        result = await llm_chat(
            [
                {"role": "system", "content": f"请提供A股「{name}」行业的最新数据，包括：行业指数点位及涨跌幅、龙头个股近期表现（3只）、近期行业政策事件（3条）、板块资金流向。用中文输出。"},
                {"role": "user", "content": f"查询行业 {name} 数据"},
            ],
            temperature=0.0, max_tokens=800,
        )
        return [("LLM行业数据", result.get("content", ""))]
    except Exception as e:
        logger.warning(f"行业数据获取失败: {e}")
        return []


async def _llm_fallback_industry(name: str) -> dict:
    """LLM 兜底获取行业数据"""
    try:
        result = await llm_chat(
            [
                {"role": "system", "content": f"提供行业 {name} 数据，JSON格式：{{\"sector_index\":数字,\"sector_change_percent\":数字,\"leading_stocks\":[],\"policy_news\":[],\"fund_flow\":\"\"}}"},
                {"role": "user", "content": f"查询 {name}"},
            ],
            temperature=0.0, max_tokens=300,
        )
        return _parse_json_from_llm(result.get("content", "")) or {}
    except Exception:
        return {}


# ---------- 交叉验证 ----------

def cross_validate_industry(results: list[dict]) -> tuple[dict, str]:
    """交叉验证行业数据"""
    if len(results) == 0:
        return {}, "低"

    best = max(results, key=lambda r: sum(1 for v in r.values() if v is not None and not str(v).startswith("_")))
    validated = {k: v for k, v in best.items() if not k.startswith("_")}

    null_count = sum(1 for v in validated.values() if v is None)
    if len(results) >= 2 and null_count <= 1:
        confidence = "高"
    elif null_count <= 2:
        confidence = "中"
    else:
        confidence = "低"

    return validated, confidence


# ---------- 辅助函数 ----------

async def _get_extraction_template(db: AsyncSession, data_type: str) -> str | None:
    """获取数据提取提示词模板"""
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE scene='data_extraction' AND is_active=1 AND is_deleted=0 LIMIT 1"),
    )
    r = row.fetchone()
    return r[0] if r else None


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
