"""行情数据查询 API"""
import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat_cache import AIChatCache
from app.schemas.common import ApiResponse
from app.services.data_engine import get_quote, get_quotes
from app.services.data_engine.base import QuoteData

logger = logging.getLogger(__name__)
router = APIRouter()


class QuoteOut(QuoteData):
    """行情输出模型（复用 QuoteData 字段）"""
    pass


# ---------- 个股简要分析（必须在 /quotes/{code} 之前注册）----------

BRIEF_ANALYSIS_PROMPT = """你是一个A股个股简要分析师。根据提供的股票行情数据，对该股票进行简要分析。

要求：
- 200字以内，精炼专业
- 小标题中必须标注数据对应的交易日期（如：### 股票名（代码）YYYY-MM-DD 行情简析）
- 包含：当前价格及涨跌情况、成交量与资金动向、近期关键事件（如有）
- 以一句话总结收尾
- 用 Markdown 格式输出，包含一个小标题和要点列表

股票数据：
{data_json}"""


@router.get("/stock/{code}/brief", response_model=ApiResponse)
async def get_stock_brief(code: str, name: str = Query(default=""), db: AsyncSession = Depends(get_db)):
    """获取个股简要分析（数据引擎 + LLM，同日同股票缓存）"""
    from config import settings

    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    today = date.today()
    cache_key = f"brief:{code}"

    # 1. 查同日缓存
    stmt = select(AIChatCache).where(
        AIChatCache.query == cache_key,
        AIChatCache.search_date == today,
    ).limit(1)
    cached = (await db.execute(stmt)).scalar_one_or_none()
    if cached:
        cached_data = json.loads(cached.response)
        cached_data["cached"] = True
        return ApiResponse(data=cached_data)

    from app.services.data_engine.assembler import fetch_stock_data

    # 2. 获取股票数据
    data_result = await fetch_stock_data(code, name or code, db)
    structured = data_result.get("structured_data", {})
    confidence = data_result.get("confidence_label", "低")

    if not structured or not structured.get("latest_price"):
        return ApiResponse(code=404, message="暂无该股票的行情数据，请稍后重试", data=None)

    # 3. 构建 prompt
    data_json = json.dumps(structured, ensure_ascii=False, indent=2)
    system_prompt = BRIEF_ANALYSIS_PROMPT.replace("{data_json}", data_json)

    # 4. 调用 LLM
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"简要分析股票 {structured.get('name', code)}"},
            ],
            max_tokens=600,
            temperature=0.3,
        )
    except Exception as e:
        logger.error(f"简要分析失败 [{code}]: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    response_data = {
        "content": result.get("content", ""),
        "confidence": confidence,
        "data_snapshot": structured,
    }

    # 5. 写入缓存
    cache_entry = AIChatCache(
        query=cache_key,
        response=json.dumps(response_data, ensure_ascii=False),
        search_date=today,
    )
    db.add(cache_entry)
    await db.flush()

    response_data["cached"] = False
    return ApiResponse(data=response_data)


@router.get("/quotes/{code}", response_model=ApiResponse[QuoteOut])
async def get_stock_quote(code: str, db: AsyncSession = Depends(get_db)):
    """获取单只股票最新行情"""
    quote = await get_quote(code, db)
    if not quote:
        return ApiResponse(code=404, message="未找到该股票行情数据", data=None)
    return ApiResponse(data=quote)


@router.get("/quotes", response_model=ApiResponse)
async def get_stock_quotes(
    codes: str = Query(..., description="股票代码，逗号分隔，如 600519,000858"),
    db: AsyncSession = Depends(get_db),
):
    """批量获取股票最新行情"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return ApiResponse(code=400, message="请提供至少一个股票代码", data=None)
    results = await get_quotes(code_list, db)
    return ApiResponse(data={"items": list(results.values()), "total": len(results)})
