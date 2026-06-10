"""LLM 兜底行业数据源

当东财 API 和 Playwright 爬虫均失败时，使用 LLM 生成行业数据。
包装现有 LLM 调用逻辑为 SectorProvider 接口。
"""
import json
import logging
import re

from app.services.data_engine.sector import SectorData, SectorProvider

logger = logging.getLogger(__name__)


class LLMSectorProvider(SectorProvider):
    name = "llm"

    async def fetch_sector(self, code: str) -> SectorData | None:
        """使用 LLM 获取行业数据（兜底，不传板块代码，用后续提供的名称）"""
        # LLM 兜底需要板块名称，代码到名称的转换由上层完成
        # 这里返回 None，由 SectorFailoverManager 在调用前转换
        return None

    async def fetch_sector_by_name(self, name: str) -> SectorData | None:
        """按板块名称获取 LLM 行业数据"""
        try:
            from app.services.llm import chat as llm_chat

            prompt = (
                f"你是A股行业数据分析专家。请提供「{name}」行业板块的最新数据，"
                f"以 JSON 格式返回，字段包括：\n"
                f'{{"sector_index": 板块指数最新点位数字,'
                f'"sector_change_percent": 板块涨跌幅百分比数字,'
                f'"leading_stocks": ["龙头个股名及近期表现", ...],'
                f'"fund_flow": "板块资金流向概况"}}\n'
                f"只输出 JSON，不要额外解释。如果某字段数据不可得，填 null。"
            )
            result = await llm_chat(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"查询{name}板块数据"},
                ],
                temperature=0.0,
                max_tokens=500,
            )
            content = result.get("content", "")
            parsed = _parse_json(content)
            if not parsed:
                return None

            # 提取 leading_stocks 为 dict 列表（LLM 可能返回字符串列表）
            leaders_raw = parsed.get("leading_stocks") or []
            leaders = []
            for item in leaders_raw:
                if isinstance(item, dict):
                    leaders.append(item)
                elif isinstance(item, str):
                    leaders.append({"name": item})

            return SectorData(
                code="",
                name=name,
                sector_index=_safe_float(parsed.get("sector_index")),
                sector_change_percent=_safe_float(parsed.get("sector_change_percent")),
                leading_stocks=leaders,
                policy_news=parsed.get("policy_news") or [],
                fund_flow=str(parsed.get("fund_flow") or ""),
                source="llm",
            )
        except Exception as e:
            logger.warning(f"LLM 行业数据获取失败 [{name}]: {e}")
            return None


def _parse_json(raw: str) -> dict | None:
    """从 LLM 响应中提取 JSON"""
    if not raw:
        return None
    # Try ```json ... ``` block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    extract = m.group(1) if m else raw
    try:
        return json.loads(extract)
    except (json.JSONDecodeError, ValueError):
        pass
    # Try { ... }
    m = re.search(r"\{[\s\S]*\}", extract)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _safe_float(v) -> float | None:
    if v is None or v == "-":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
