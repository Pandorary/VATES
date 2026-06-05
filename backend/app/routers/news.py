"""资讯查询 API"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.news import NewsOut, NewsListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/news", response_model=ApiResponse[NewsListResponse])
async def list_news(
    code: str | None = Query(None, description="股票代码，不传返回全部（含宏观）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """分页查询新闻列表"""
    offset = (page - 1) * page_size

    where = ""
    params = {"limit": page_size, "offset": offset}
    if code:
        where = "WHERE code = :code"
        params["code"] = code

    # 总数
    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM news {where}"), params
    )
    total = count_row.scalar() or 0

    # 分页数据
    rows = await db.execute(
        text(f"""
            SELECT id, code, title, url, source_site, publish_time, content_preview
            FROM news {where}
            ORDER BY publish_time DESC, id DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    items = [
        NewsOut(
            id=r[0], code=r[1], title=r[2], url=r[3],
            source_site=r[4], publish_time=r[5], content_preview=r[6],
        )
        for r in rows.fetchall()
    ]

    return ApiResponse(
        data=NewsListResponse(items=items, total=total, page=page, page_size=page_size)
    )


@router.get("/news/{code}", response_model=ApiResponse[NewsListResponse])
async def get_stock_news(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """查询指定股票的新闻"""
    offset = (page - 1) * page_size

    count_row = await db.execute(
        text("SELECT COUNT(*) FROM news WHERE code = :code"),
        {"code": code},
    )
    total = count_row.scalar() or 0

    rows = await db.execute(
        text("""
            SELECT id, code, title, url, source_site, publish_time, content_preview
            FROM news WHERE code = :code
            ORDER BY publish_time DESC, id DESC
            LIMIT :limit OFFSET :offset
        """),
        {"code": code, "limit": page_size, "offset": offset},
    )
    items = [
        NewsOut(
            id=r[0], code=r[1], title=r[2], url=r[3],
            source_site=r[4], publish_time=r[5], content_preview=r[6],
        )
        for r in rows.fetchall()
    ]

    return ApiResponse(
        data=NewsListResponse(items=items, total=total, page=page, page_size=page_size)
    )
