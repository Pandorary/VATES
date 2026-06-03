"""搜索分类 + 行业分析"""
import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from config import settings
from app.schemas.common import ApiResponse
from app.models.industry_cache import IndustryAnalysisCache

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------- 内存缓存：分类结果不变，无需持久化 ----------
_classify_cache: dict[str, dict] = {}

# ---------- 分类 prompt ----------
_CLASSIFY_SYSTEM_PROMPT = """你是一个A股搜索意图分类器。根据用户输入，判断其搜索目标类型。

分类规则：
- 个股：输入是A股股票代码（如600519、000001）或股票名称（如贵州茅台、比亚迪）
- 行业：输入是A股行业板块名称（如白酒、新能源汽车、半导体、医药）
- 其他：既不是个股也不是行业

请严格按以下JSON格式输出，不要输出任何其他内容：
{"type":"stock|industry|unknown","name":"标准化名称"}

示例：
- "600519" → {"type":"stock","name":"贵州茅台"}
- "贵州茅台" → {"type":"stock","name":"贵州茅台"}
- "白酒" → {"type":"industry","name":"白酒"}
- "半导体" → {"type":"industry","name":"半导体"}
- "天气" → {"type":"unknown","name":"天气"}"""

# ---------- 行业分析 fallback prompt ----------
_INDUSTRY_FALLBACK_PROMPT = """你是一位资深A股行业研究员。请对「{query}」行业进行全面深入的分析。

请按以下板块输出，每个板块用Markdown二级标题分隔：

## 行业概览
行业定义、规模、发展阶段

## 龙头企业
列出3-5家代表性上市公司，简要说明其地位

## 行业趋势
当前发展趋势、技术变革、增长驱动力

## 政策影响
相关政策法规及其对行业的影响

## 估值水平
行业整体估值、与历史水平比较

## 风险提示
行业面临的主要风险

## 投资结论
综合研判与投资建议

要求：
- 用中文输出
- 用 Markdown 格式
- 内容详实，有数据支撑
- 注明仅供参考，不构成投资建议"""


# ---------- 搜索分类 ----------

class SearchRequest(BaseModel):
    query: str = Field(..., description="用户搜索关键词")


@router.post("/search", response_model=ApiResponse)
async def search_classify(body: SearchRequest):
    """LLM 判断输入是个股、行业还是其他"""
    query = body.query.strip()
    if not query:
        return ApiResponse(code=400, message="请输入搜索关键词", data=None)

    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    # 1. 查内存缓存
    if query in _classify_cache:
        return ApiResponse(data={**_classify_cache[query], "cached": True})

    # 2. 调 LLM 分类
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat(
            [
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=100,
            temperature=0.0,
        )
    except Exception as e:
        logger.error(f"搜索分类失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    # 3. 解析 JSON
    content = result.get("content", "")
    classify_result = _parse_classify_json(content, query)
    _classify_cache[query] = classify_result

    return ApiResponse(data={**classify_result, "cached": False})


def _parse_classify_json(raw: str, fallback_name: str) -> dict:
    """解析 LLM 返回的分类 JSON，失败时 fallback"""
    import re

    # 尝试从 markdown 代码块中提取
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
    extract = json_match.group(1) if json_match else raw

    # 尝试直接解析
    try:
        data = json.loads(extract)
        type_ = data.get("type", "unknown")
        if type_ not in ("stock", "industry", "unknown"):
            type_ = "unknown"
        name = data.get("name") or fallback_name
        return {"type": type_, "name": str(name)}
    except (json.JSONDecodeError, AttributeError):
        pass

    # 尝试提取花括号内的 JSON
    try:
        brace_match = re.search(r"\{[\s\S]*\}", raw)
        if brace_match:
            data = json.loads(brace_match.group())
            type_ = data.get("type", "unknown")
            if type_ not in ("stock", "industry", "unknown"):
                type_ = "unknown"
            name = data.get("name") or fallback_name
            return {"type": type_, "name": str(name)}
    except (json.JSONDecodeError, AttributeError):
        pass

    return {"type": "unknown", "name": fallback_name}


# ---------- 行业分析 ----------

class IndustryAnalysisRequest(BaseModel):
    query: str = Field(..., description="行业板块名称")


async def _get_industry_template(db: AsyncSession) -> str | None:
    """获取 industry_analysis 提示词模板"""
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE skill='industry_analysis' AND is_active=1 AND is_deleted=0 LIMIT 1"),
    )
    r = row.fetchone()
    return r[0] if r else None


@router.post("/industry-analysis", response_model=ApiResponse)
async def industry_analysis(body: IndustryAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """行业分析（同天同行业缓存）"""
    query = body.query.strip()
    if not query:
        return ApiResponse(code=400, message="请输入行业名称", data=None)

    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data={"content": "请在 .env 中设置 LLM_API_KEY"})

    from datetime import date

    today = date.today()

    # 1. 查缓存
    stmt = select(IndustryAnalysisCache).where(
        IndustryAnalysisCache.query == query,
        IndustryAnalysisCache.search_date == today,
    ).limit(1)
    cached = (await db.execute(stmt)).scalar_one_or_none()
    if cached:
        return ApiResponse(data={"content": cached.response, "cached": True})

    # 2. 取模板，无模板则用 fallback
    template = await _get_industry_template(db)
    if template:
        system_prompt = template.replace("{{query}}", query)
    else:
        system_prompt = _INDUSTRY_FALLBACK_PROMPT.format(query=query)

    # 3. 调 LLM
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析行业：{query}"},
        ])
    except Exception as e:
        logger.error(f"行业分析失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    # 4. 写入缓存
    content = result.get("content", "")
    cache_entry = IndustryAnalysisCache(
        query=query, response=content, search_date=today,
    )
    db.add(cache_entry)
    await db.flush()

    return ApiResponse(data={"content": content, "cached": False})
