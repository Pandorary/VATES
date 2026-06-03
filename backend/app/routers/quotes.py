"""行情数据查询 API"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.services.quotes import get_quote, get_quotes
from app.services.quotes.base import QuoteData

logger = logging.getLogger(__name__)
router = APIRouter()


class QuoteOut(QuoteData):
    """行情输出模型（复用 QuoteData 字段）"""
    pass


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
