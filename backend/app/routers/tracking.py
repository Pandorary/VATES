"""预测跟踪 CRUD + 偏离分析"""
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from config import settings
from app.schemas.common import ApiResponse
from app.models.tracking import PredictionTracking

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------- 请求/响应模型 ----------

class TrackingCreate(BaseModel):
    type: str = Field(..., description="stock / industry")
    name: str = Field(..., description="股票或行业名称")


class TrackingOut(BaseModel):
    id: int
    type: str
    name: str
    created_at: str | None


def _row_to_out(r) -> TrackingOut:
    return TrackingOut(
        id=r[0], type=r[1], name=r[2],
        created_at=str(r[3]) if r[3] else None,
    )


class DeviationRequest(BaseModel):
    name: str = Field(..., description="标的名称")
    type: str = Field("stock", description="stock / industry")


HORIZON_ORDER = ["tomorrow", "week", "1-3m", "3m+"]


# ---------- CRUD ----------

@router.get("/tracking", response_model=ApiResponse)
async def list_tracking(db: AsyncSession = Depends(get_db)):
    """获取跟踪列表"""
    rows = await db.execute(
        text("SELECT id, type, name, created_at FROM prediction_tracking WHERE is_deleted=0 ORDER BY created_at DESC")
    )
    items = [_row_to_out(r) for r in rows.fetchall()]
    return ApiResponse(data=[{"id": it.id, "type": it.type, "name": it.name, "created_at": it.created_at} for it in items])


@router.post("/tracking", response_model=ApiResponse)
async def add_tracking(body: TrackingCreate, db: AsyncSession = Depends(get_db)):
    """加入跟踪（去重）"""
    body.type = body.type.strip()
    body.name = body.name.strip()
    if not body.name:
        return ApiResponse(code=400, message="名称不能为空", data=None)
    if body.type not in ("stock", "industry"):
        return ApiResponse(code=400, message="类型无效", data=None)

    # 去重检查
    existing = await db.execute(
        text("SELECT id FROM prediction_tracking WHERE type=:type AND name=:name AND is_deleted=0 LIMIT 1"),
        {"type": body.type, "name": body.name},
    )
    if existing.fetchone():
        return ApiResponse(code=409, message="已在跟踪列表中", data=None)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        text("INSERT INTO prediction_tracking (type, name, is_deleted, created_at) VALUES (:type, :name, 0, :now)"),
        {"type": body.type, "name": body.name, "now": now},
    )
    await db.flush()
    return ApiResponse(data={"added": True})


@router.delete("/tracking/{tracking_id}", response_model=ApiResponse)
async def remove_tracking(tracking_id: int, db: AsyncSession = Depends(get_db)):
    """取消跟踪（软删除）"""
    row = await db.execute(
        text("SELECT 1 FROM prediction_tracking WHERE id=:id AND is_deleted=0"),
        {"id": tracking_id},
    )
    if not row.fetchone():
        return ApiResponse(code=404, message="跟踪项不存在", data=None)

    await db.execute(
        text("UPDATE prediction_tracking SET is_deleted=1 WHERE id=:id"),
        {"id": tracking_id},
    )
    await db.flush()
    return ApiResponse(data={"deleted": True})


# ---------- 最新预测 ----------

@router.get("/tracking/{tracking_id}/latest-prediction", response_model=ApiResponse)
async def latest_prediction(tracking_id: int, db: AsyncSession = Depends(get_db)):
    """获取该跟踪标的最新预测结果（每个时段最新一条）"""
    # 先查跟踪项
    row = await db.execute(
        text("SELECT type, name FROM prediction_tracking WHERE id=:id AND is_deleted=0"),
        {"id": tracking_id},
    )
    item = row.fetchone()
    if not item:
        return ApiResponse(code=404, message="跟踪项不存在", data=None)

    name = item[1]

    # 每个 horizon 取最新一条
    predictions = {}
    for horizon in HORIZON_ORDER:
        pr = await db.execute(
            text("SELECT response, search_date, created_at FROM prediction_cache WHERE query=:q AND horizon=:h ORDER BY search_date DESC, created_at DESC LIMIT 1"),
            {"q": name, "h": horizon},
        )
        r = pr.fetchone()
        if r:
            predictions[horizon] = {
                "content": r[0],
                "search_date": str(r[1]),
                "created_at": str(r[2]),
            }

    return ApiResponse(data={"name": name, "type": item[0], "predictions": predictions})


# ---------- 偏离分析 ----------

DEVIATION_PROMPT = """你是一位A股风险管理分析师。请对比以下信息，判断实际走势是否偏离了 AI 预测，并给出风控建议。

## AI 预测内容
{predictions}

## 近期实际走势
{price_data}

要求：
1. 判断走势是否偏离预测方向（符合/部分偏离/明显偏离）
2. 分析偏离原因（如有）
3. 给出风控建议
4. 用中文输出，Markdown 格式
5. 注明仅供参考，不构成投资建议"""


@router.post("/tracking/deviation-analysis", response_model=ApiResponse)
async def deviation_analysis(body: DeviationRequest, db: AsyncSession = Depends(get_db)):
    """分析预测 vs 实际走势偏离"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    name = body.name.strip()

    # 1. 取最新预测（所有 horizon）
    pred_parts = []
    for horizon in HORIZON_ORDER:
        pr = await db.execute(
            text("SELECT response FROM prediction_cache WHERE query=:q AND horizon=:h ORDER BY search_date DESC LIMIT 1"),
            {"q": name, "h": horizon},
        )
        r = pr.fetchone()
        if r:
            pred_parts.append(f"### {horizon}\n{r[0]}")

    if not pred_parts:
        return ApiResponse(code=404, message="该标的暂无预测数据，请先生成预测", data=None)

    predictions_text = "\n\n".join(pred_parts)

    # 2. 取近期价格数据（仅个股）
    price_text = "无直接价格数据（行业）"
    if body.type == "stock":
        stock_row = await db.execute(
            text("SELECT code FROM stocks WHERE name=:name LIMIT 1"),
            {"name": name},
        )
        stock = stock_row.fetchone()
        if stock:
            code = stock[0]
            quotes = await db.execute(
                text("SELECT trade_date, open, high, low, close, change_pct, volume FROM daily_quotes WHERE code=:code ORDER BY trade_date DESC LIMIT 10"),
                {"code": code},
            )
            rows = quotes.fetchall()
            if rows:
                lines = ["| 日期 | 开盘 | 最高 | 最低 | 收盘 | 涨跌幅% | 成交量(手) |",
                          "|------|------|------|------|------|---------|------------|"]
                for r in rows:
                    lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |")
                price_text = "\n".join(lines)
            else:
                price_text = "暂无该股票近期行情数据"
        else:
            price_text = "未在股票数据库中找到该标的"

    # 3. 调 LLM
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": DEVIATION_PROMPT.format(
                predictions=predictions_text[:6000],
                price_data=price_text,
            )},
            {"role": "user", "content": f"分析{name}的预测偏离情况"},
        ])
    except Exception as e:
        logger.error(f"偏离分析失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    return ApiResponse(data={"content": result.get("content", ""), "price_data": price_text})
