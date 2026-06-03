"""智能数据引擎 — 多源抓取、交叉验证、置信度分类

注意: _fetch_stock_raw() 中的 HTTP 行情获取逻辑已迁移至
app.services.quotes 包（腾讯/东方财富/新浪适配器 + TTL 缓存 + 定时采集）。
本模块仍为 prediction.py 提供完整的 LLM 结构化提取能力，
未来可重构为使用 quotes 包获取行情数据。
"""
import json
import logging
import re
from datetime import date, datetime

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import chat as llm_chat
from config import settings

logger = logging.getLogger(__name__)

# ---------- 信源白名单 ----------
STOCK_DATA_SOURCES = [
    {
        "name": "东方财富",
        "url_template": "https://push2.eastmoney.com/api/qt/stock/get?secid=1.{code}&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f170",
        "type": "api",
    },
    {
        "name": "新浪财经",
        "url_template": "https://hq.sinajs.cn/list={prefix}{code}",
        "type": "text",
    },
]

INDUSTRY_SEARCH_QUERIES = [
    'site:eastmoney.com {{industry}} 行业指数 龙头',
    'site:finance.sina.com.cn {{industry}} 板块 行情',
]

# ---------- 数据提取提示词模板 ----------
DATA_EXTRACTION_PROMPT_STOCK = """你是一个严格的数据提取器。你的唯一任务是从提供的原始文本中提取结构化数据。

严禁进行任何预测、分析或推断。只提取明确出现在文本中的数据。

请提取以下字段并以 JSON 格式输出：

{{
  "latest_close_price": "前一交易日收盘价（数字）",
  "open_price": "前一交易日开盘价（数字）",
  "high_price": "前一交易日最高价（数字）",
  "low_price": "前一交易日最低价（数字）",
  "price_change_percent": "涨跌幅%（数字）",
  "volume": "成交量（数字，单位：手）",
  "key_events": ["近3日重要公告或新闻标题，最多5条"],
  "trade_date": "数据对应的交易日期（YYYY-MM-DD）"
}}

如果某个字段在原始文本中找不到，填 null。不要编造数据。

原始数据如下：
{raw_data}
"""

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


# ---------- 个股数据抓取 ----------

async def fetch_stock_data(code: str, name: str, db: AsyncSession) -> dict:
    """多源抓取个股数据，交叉验证，返回结构化数据+置信度"""
    today = date.today()
    results = []

    # 1. 从多个信源抓取原始数据
    raw_texts = await _fetch_stock_raw(code, name)

    # 2. 获取数据提取提示词模板
    template = await _get_extraction_template(db, "stock")

    # 3. 对每个信源的数据调用 LLM 提取结构化数据
    for source_name, raw_text in raw_texts:
        if not raw_text:
            continue
        try:
            prompt = template or DATA_EXTRACTION_PROMPT_STOCK
            prompt = prompt.replace("{raw_data}", raw_text[:4000])
            result = await llm_chat(
                [{"role": "system", "content": prompt}, {"role": "user", "content": f"提取股票 {code}({name}) 的数据"}],
                temperature=0.0, max_tokens=1000,
            )
            structured = _parse_json_from_llm(result.get("content", ""))
            if structured:
                structured["_source"] = source_name
                results.append(structured)
        except Exception as e:
            logger.warning(f"数据提取失败 [{source_name}]: {e}")

    # 4. 交叉验证
    if not results:
        # fallback: 用 LLM 直接获取（兼容旧逻辑）
        fallback = await _llm_fallback_stock(code, name)
        return {
            "structured_data": fallback,
            "confidence_label": "低",
            "source_urls": [],
            "fetch_timestamp": datetime.now().isoformat(),
        }

    validated, confidence = cross_validate_stock(results)

    return {
        "structured_data": validated,
        "confidence_label": confidence,
        "source_urls": [f"{s}:{r.get('_source', '')}" for r in results for s in [code]],
        "fetch_timestamp": datetime.now().isoformat(),
    }


async def _fetch_stock_raw(code: str, name: str) -> list[tuple[str, str]]:
    """从多个信源获取原始数据"""
    results = []

    # 东方财富 API
    try:
        # 判断沪市(1)还是深市(0)
        market = "1" if code.startswith(("6", "9")) else "0"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f170,f171"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                results.append(("东方财富", resp.text))
    except Exception as e:
        logger.warning(f"东方财富抓取失败: {e}")

    # 新浪财经
    try:
        prefix = "sh" if code.startswith(("6", "9")) else "sz"
        url = f"https://hq.sinajs.cn/list={prefix}{code}"
        async with httpx.AsyncClient(timeout=10, headers={"Referer": "https://finance.sina.com.cn"}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                results.append(("新浪财经", resp.text))
    except Exception as e:
        logger.warning(f"新浪财经抓取失败: {e}")

    # 如果直接抓取都失败了，用 LLM 搜索（最后手段）
    if not results:
        try:
            search_result = await llm_chat(
                [
                    {"role": "system", "content": f"请提供股票 {code}({name}) 今天的行情数据（开盘价、收盘价、最高价、最低价、涨跌幅、成交量）。严格按JSON输出。"},
                    {"role": "user", "content": f"查询 {code}({name}) 最新行情"},
                ],
                temperature=0.0, max_tokens=500,
            )
            content = search_result.get("content", "")
            results.append(("LLM搜索", content))
        except Exception as e:
            logger.warning(f"LLM搜索失败: {e}")

    return results


async def _llm_fallback_stock(code: str, name: str) -> dict:
    """LLM 直接获取股票数据（最终兜底）"""
    try:
        result = await llm_chat(
            [
                {"role": "system", "content": f"请提供股票 {code}({name}) 的最新行情数据。严格按JSON输出：{{\"latest_close_price\":数字,\"open_price\":数字,\"high_price\":数字,\"low_price\":数字,\"price_change_percent\":数字,\"volume\":数字}}"},
                {"role": "user", "content": f"查询 {code}({name})"},
            ],
            temperature=0.0, max_tokens=300,
        )
        data = _parse_json_from_llm(result.get("content", ""))
        return data or {}
    except Exception:
        return {}


# ---------- 行业数据抓取 ----------

async def fetch_industry_data(name: str, db: AsyncSession) -> dict:
    """多源抓取行业数据"""
    results = []

    # 用 LLM 获取行业数据（MVP 阶段）
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

def cross_validate_stock(results: list[dict]) -> tuple[dict, str]:
    """交叉验证个股数据，返回 (验证后数据, 置信度标签)"""
    if len(results) == 0:
        return {}, "低"

    if len(results) == 1:
        data = {k: v for k, v in results[0].items() if not k.startswith("_")}
        # 单信源 → 中置信度
        null_count = sum(1 for v in data.values() if v is None)
        confidence = "中" if null_count <= 2 else "低"
        return data, confidence

    # 多信源：多数投票
    validated = {}
    numeric_fields = ["latest_close_price", "open_price", "high_price", "low_price", "price_change_percent", "volume"]

    for field in numeric_fields:
        values = []
        for r in results:
            v = r.get(field)
            if v is not None:
                try:
                    values.append(float(v))
                except (ValueError, TypeError):
                    pass

        if not values:
            validated[field] = None
            continue

        if len(values) >= 2:
            # 检查一致性（允许5%偏差）
            avg = sum(values) / len(values)
            consistent = all(abs(v - avg) / max(abs(avg), 0.01) < 0.05 for v in values)
            if consistent:
                validated[field] = round(sum(values) / len(values), 3)
            else:
                # 冲突标记
                validated[field] = round(sum(values) / len(values), 3)
                validated[f"{field}_conflict"] = True
        else:
            validated[field] = values[0]

    # 非数值字段取第一个有效值
    for field in ["key_events", "trade_date"]:
        for r in results:
            v = r.get(field)
            if v is not None:
                validated[field] = v
                break

    # 置信度判定
    has_conflict = any(k.endswith("_conflict") for k in validated)
    null_count = sum(1 for k, v in validated.items() if v is None and not k.endswith("_conflict"))

    if has_conflict:
        confidence = "低"
    elif null_count <= 1:
        confidence = "高"
    else:
        confidence = "中"

    return validated, confidence


def cross_validate_industry(results: list[dict]) -> tuple[dict, str]:
    """交叉验证行业数据"""
    if len(results) == 0:
        return {}, "低"

    # 行业数据以第一个完整结果为主
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

    # 尝试从 markdown 代码块中提取
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
    extract = json_match.group(1) if json_match else raw

    try:
        return json.loads(extract)
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试提取花括号内的 JSON
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
