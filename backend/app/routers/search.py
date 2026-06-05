"""搜索分类"""
import json
import re
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from app.database import get_db
from app.schemas.common import ApiResponse

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


# ---------- 搜索分类 ----------

class SearchRequest(BaseModel):
    query: str = Field(..., description="用户搜索关键词")


async def _lookup_stock_code(name: str, db: AsyncSession) -> str | None:
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


def _is_stock_code(s: str) -> bool:
    """判断是否为 6 位数字股票代码"""
    return bool(re.fullmatch(r"\d{6}", s))


@router.post("/search", response_model=ApiResponse)
async def search_classify(body: SearchRequest, db: AsyncSession = Depends(get_db)):
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

    # 4. 个股：补全股票代码
    if classify_result.get("type") == "stock" and not classify_result.get("code"):
        code = None
        # 原始输入是 6 位数字 → 直接作为代码
        if _is_stock_code(query):
            code = query
        else:
            # 按标准化名称查数据库
            code = await _lookup_stock_code(classify_result["name"], db)
            if not code:
                # 按原始输入查数据库
                code = await _lookup_stock_code(query, db)
        if code:
            classify_result["code"] = code

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
