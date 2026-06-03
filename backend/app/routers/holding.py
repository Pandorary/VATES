"""持仓股 CRUD + AI 诊断"""
import logging
from datetime import datetime
import json
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from config import settings
from app.schemas.common import ApiResponse
from app.schemas.holding import (
    HoldingOut,
    HoldingCreateIn,
    HoldingUpdateIn,
    HoldingListOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# MVP 阶段固定 user_id
DEFAULT_USER_ID = 1

DIAGNOSE_PROMPT = """你是一位资深A股投资顾问。请根据以下持仓信息，给出诊断和操作建议。

## 持仓信息
- 股票：{name}（{code}）
- 成本价：{cost_price} 元
- 当前价：{current_price} 元
- 持仓数量：{shares} 股
- 持仓市值：{market_value} 元
- 盈亏金额：{profit_amount} 元
- 盈亏比例：{profit_pct}%

## 近期走势
{recent_quotes}

请按以下结构输出诊断报告（用 Markdown 格式，中文）：

## 持仓诊断
对当前持仓状态进行评价（盈利/亏损程度、是否处于关键价位等）

## 技术面分析
基于近期走势的技术分析（趋势、支撑/压力位等）

## 操作建议
给出明确的操作建议（加仓/持有/减仓/止损），并说明理由和具体操作价位

## 风险提示
需要注意的风险因素

注明：以上为 AI 分析，仅供参考，不构成投资建议"""


SELECT_SQL = """
SELECT h.id, h.code, h.name, h.cost_price, h.shares, h.total_assets, h.created_at, h.updated_at,
       s.name AS stock_name
FROM holdings h
LEFT JOIN stocks s ON s.code = h.code
WHERE h.is_deleted = 0 AND h.user_id = :uid
"""


@router.get("/holdings", response_model=ApiResponse[HoldingListOut])
async def list_holdings(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        text(SELECT_SQL + " ORDER BY h.created_at DESC"),
        {"uid": DEFAULT_USER_ID},
    )
    raw_rows = rows.fetchall()

    if not raw_rows:
        return ApiResponse(data=HoldingListOut(items=[], total=0))

    # 收集所有唯一股票代码
    codes = list(set(r[1] for r in raw_rows if r[1]))

    # 批量获取行情数据（真实 API，非 LLM）
    from app.services.quotes import get_quotes
    prices: dict = {}
    if codes:
        try:
            prices = await get_quotes(codes, db)
        except Exception as e:
            logger.warning(f"行情批量查询失败: {e}")

    items = []
    for r in raw_rows:
        code = r[1] or ""
        name = r[2] or r[7] or ""
        cost_price = float(r[3] or 0)
        shares = int(r[4] or 0)

        # 使用真实行情数据
        quote = prices.get(code)
        current_price = quote.price if quote else None
        if quote and quote.name:
            name = quote.name

        profit_amount = None
        profit_pct = None
        if current_price is not None and shares:
            profit_amount = round((current_price - cost_price) * shares, 2)
            if cost_price > 0:
                profit_pct = round((current_price - cost_price) / cost_price * 100, 2)

        items.append(HoldingOut(
            id=r[0], code=code, name=name,
            cost_price=cost_price, shares=shares, total_assets=float(r[5] or 0),
            current_price=current_price,
            profit_amount=profit_amount,
            profit_pct=profit_pct,
            created_at=str(r[6]) if r[6] else None,
            updated_at=str(r[7]) if r[7] else None,
        ))

    return ApiResponse(data=HoldingListOut(items=items, total=len(items)))


# ---------- 用户总资产 ----------

class TotalAssetsUpdate(BaseModel):
    value: float = Field(..., description="总资产金额")


@router.get("/holdings/total-assets", response_model=ApiResponse)
async def get_total_assets(db: AsyncSession = Depends(get_db)):
    """获取用户总资产"""
    row = await db.execute(
        text("SELECT value FROM user_config WHERE user_id=:uid AND key='total_assets'"),
        {"uid": DEFAULT_USER_ID},
    )
    r = row.fetchone()
    value = float(r[0]) if r else 0
    return ApiResponse(data={"value": value})


@router.put("/holdings/total-assets", response_model=ApiResponse)
async def update_total_assets(body: TotalAssetsUpdate, db: AsyncSession = Depends(get_db)):
    """更新用户总资产"""
    if body.value < 0:
        return ApiResponse(code=400, message="总资产不能为负数", data=None)

    await db.execute(
        text("""INSERT INTO user_config (user_id, key, value, updated_at)
                VALUES (:uid, 'total_assets', :val, datetime('now', 'localtime'))
                ON CONFLICT(user_id, key) DO UPDATE SET value=:val2, updated_at=datetime('now', 'localtime')"""),
        {"uid": DEFAULT_USER_ID, "val": str(body.value), "val2": str(body.value)},
    )
    await db.flush()
    return ApiResponse(data={"value": body.value})


PRICE_PROMPT = """deprecated — no longer used"""


@router.post("/holdings", response_model=ApiResponse[HoldingOut])
async def create_holding(body: HoldingCreateIn, db: AsyncSession = Depends(get_db)):
    code = body.code.strip()
    if not code:
        return ApiResponse(code=400, message="股票代码不能为空", data=None)

    # 获取股票名称和当前价格（真实 API）
    from app.services.quotes import get_quote
    name_val = ""
    current_price = None
    try:
        quote = await get_quote(code, db)
        if quote:
            name_val = quote.name
            current_price = quote.price
    except Exception as e:
        logger.error(f"行情查询失败: {e}")
        return ApiResponse(code=500, message=f"行情查询失败：{e}", data=None)

    if not name_val or not current_price:
        return ApiResponse(code=500, message="未能获取股票信息，请检查代码是否正确", data=None)

    # 计算盈亏
    cost_price = body.cost_price
    shares = body.shares
    total_assets = body.total_assets
    profit_amount = round(total_assets - cost_price * shares, 2)
    profit_pct = round(profit_amount / (cost_price * shares) * 100, 2) if cost_price * shares > 0 else None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = await db.execute(
        text("""INSERT INTO holdings (user_id, code, name, cost_price, shares, total_assets, is_deleted, created_at, updated_at)
                VALUES (:uid, :code, :name, :cp, :sh, :ta, 0, :now, :now)"""),
        {"uid": DEFAULT_USER_ID, "code": code, "name": name_val,
         "cp": cost_price, "sh": shares, "ta": total_assets, "now": now},
    )
    await db.flush()

    new_id = result.lastrowid
    return ApiResponse(data=HoldingOut(
        id=new_id, code=code, name=name_val,
        cost_price=cost_price, shares=shares, total_assets=total_assets,
        current_price=current_price,
        profit_amount=profit_amount, profit_pct=profit_pct,
        created_at=now, updated_at=now,
    ))


@router.put("/holdings/{holding_id}", response_model=ApiResponse[HoldingOut])
async def update_holding(holding_id: int, body: HoldingUpdateIn, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT id, code, name, cost_price, shares, created_at FROM holdings WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": holding_id, "uid": DEFAULT_USER_ID},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="持仓不存在", data=None)

    cost_price = body.cost_price if body.cost_price is not None else float(existing[3])
    shares = body.shares if body.shares is not None else int(existing[4])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await db.execute(
        text("UPDATE holdings SET cost_price=:cp, shares=:sh, updated_at=:now WHERE id=:id"),
        {"cp": cost_price, "sh": shares, "now": now, "id": holding_id},
    )
    await db.flush()

    # 获取当前行情
    code = existing[1]
    name = existing[2] or ""
    current_price = None
    try:
        from app.services.quotes import get_quote
        quote = await get_quote(code, db)
        if quote:
            name = quote.name or name
            current_price = quote.price
    except Exception as e:
        logger.warning(f"行情查询失败: {e}")

    profit_amount = None
    profit_pct = None
    if current_price is not None and shares:
        profit_amount = round((current_price - cost_price) * shares, 2)
        if cost_price > 0:
            profit_pct = round((current_price - cost_price) / cost_price * 100, 2)

    return ApiResponse(data=HoldingOut(
        id=existing[0], code=code, name=name,
        cost_price=cost_price, shares=shares,
        current_price=current_price,
        profit_amount=profit_amount, profit_pct=profit_pct,
        created_at=str(existing[5]) if len(existing) > 5 else None,
        updated_at=now,
    ))


@router.delete("/holdings/{holding_id}", response_model=ApiResponse)
async def delete_holding(holding_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT 1 FROM holdings WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": holding_id, "uid": DEFAULT_USER_ID},
    )
    if not row.fetchone():
        return ApiResponse(code=404, message="持仓不存在", data=None)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        text("UPDATE holdings SET is_deleted=1, updated_at=:now WHERE id=:id"),
        {"now": now, "id": holding_id},
    )
    await db.flush()
    return ApiResponse(data={"deleted": True})


# ---------- AI 诊断 ----------

class DiagnoseResponse(BaseModel):
    content: str = Field(..., description="诊断报告 Markdown")


@router.post("/holdings/{holding_id}/refresh", response_model=ApiResponse)
async def refresh_holding_price(holding_id: int, db: AsyncSession = Depends(get_db)):
    """刷新单个持仓的当前价格"""
    # 获取持仓信息
    row = await db.execute(
        text("SELECT id, code, name, cost_price, shares FROM holdings WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": holding_id, "uid": DEFAULT_USER_ID},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="持仓不存在", data=None)

    code = existing[1]

    # 通过行情管理器获取最新价格
    from app.services.quotes import get_quote
    try:
        quote = await get_quote(code, db)
        if not quote:
            return ApiResponse(code=500, message="无法获取股价信息", data=None)

        name = quote.name or existing[2]
        current_price = quote.price

        # 更新持仓中的股票名称（如果需要）
        if name and name != existing[2]:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                text("UPDATE holdings SET name=:name, updated_at=:now WHERE id=:id"),
                {"name": name, "now": now, "id": holding_id},
            )

        return ApiResponse(data={
            "code": code,
            "name": name,
            "current_price": current_price,
            "source": quote.source,
        })
    except Exception as e:
        logger.error(f"刷新股价失败: {e}")
        return ApiResponse(code=500, message=f"股价查询失败：{e}", data=None)


@router.post("/holdings/{holding_id}/diagnose", response_model=ApiResponse)
async def diagnose_holding(holding_id: int, db: AsyncSession = Depends(get_db)):
    """AI 诊断持仓，给出操作建议（含情景推演）"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    # 取持仓
    row = await db.execute(
        text("SELECT id, code, name, cost_price, shares, created_at FROM holdings WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": holding_id, "uid": DEFAULT_USER_ID},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="持仓不存在", data=None)

    code = existing[1]
    name = existing[2] or ""
    cost_price = float(existing[3] or 0)
    shares = int(existing[4] or 0)

    # 获取当前行情
    current_price = None
    try:
        from app.services.quotes import get_quote
        quote = await get_quote(code, db)
        if quote:
            name = quote.name or name
            current_price = quote.price
    except Exception as e:
        logger.warning(f"诊断-行情查询失败: {e}")

    if current_price is None:
        current_price = cost_price  # fallback

    market_value = round(current_price * shares, 2)
    profit_amount = round((current_price - cost_price) * shares, 2)
    profit_pct = round((current_price - cost_price) / cost_price * 100, 2) if cost_price > 0 else 0

    # 取近 10 日走势
    quotes = await db.execute(
        text("SELECT trade_date, open, high, low, close, change_pct FROM daily_quotes WHERE code=:code ORDER BY trade_date DESC LIMIT 10"),
        {"code": code},
    )
    qrows = quotes.fetchall()
    if qrows:
        lines = ["| 日期 | 开盘 | 最高 | 最低 | 收盘 | 涨跌幅% |",
                  "|------|------|------|------|------|---------|"]
        for r in reversed(qrows):
            lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
        recent = "\n".join(lines)
    else:
        recent = "暂无近期行情数据"

    # 优先使用 scene 提示词模板，fallback 到硬编码
    from app.services.data_engine import get_active_template
    template = await get_active_template(db, "position_diagnosis")

    if template:
        system_prompt = template.replace("{{name}}", name).replace("{{code}}", code)
        system_prompt = system_prompt.replace("{{cost_price}}", str(cost_price))
        system_prompt = system_prompt.replace("{{current_price}}", str(current_price))
        system_prompt = system_prompt.replace("{{shares}}", str(shares))
        system_prompt = system_prompt.replace("{{market_value}}", str(market_value))
        system_prompt = system_prompt.replace("{{profit_amount}}", str(profit_amount))
        system_prompt = system_prompt.replace("{{profit_pct}}", str(profit_pct))
        system_prompt = system_prompt.replace("{{recent_quotes}}", recent)
    else:
        system_prompt = DIAGNOSE_PROMPT.format(
            name=name, code=code,
            cost_price=cost_price, current_price=current_price,
            shares=shares, market_value=market_value,
            profit_amount=profit_amount,
            profit_pct=profit_pct,
            recent_quotes=recent,
        )

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"诊断我的持仓：{name}（{code}）"},
        ])
    except Exception as e:
        logger.error(f"持仓诊断失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    return ApiResponse(data={"content": result.get("content", "")})


# ---------- 持仓复盘 ----------

@router.post("/holdings/{holding_id}/review", response_model=ApiResponse)
async def review_holding(holding_id: int, db: AsyncSession = Depends(get_db)):
    """持仓复盘 — 对比前期诊断结论与实际走势"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    row = await db.execute(
        text("SELECT id, code, name, cost_price, shares FROM holdings WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": holding_id, "uid": DEFAULT_USER_ID},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="持仓不存在", data=None)

    code = existing[1]
    name = existing[2] or ""

    from app.services.data_engine import get_active_template
    template = await get_active_template(db, "position_review")

    if not template:
        return ApiResponse(code=400, message="当前AI模板未配置，请联系管理员", data=None)

    # 获取当前行情
    current_price = None
    try:
        from app.services.quotes import get_quote
        quote = await get_quote(code, db)
        if quote:
            current_price = quote.price
    except Exception:
        pass

    if current_price is None:
        current_price = float(existing[3] or 0)

    system_prompt = template.replace("{{name}}", name).replace("{{code}}", code)
    system_prompt = system_prompt.replace("{{current_price}}", str(current_price))

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"复盘持仓 {name}（{code}）"},
        ])
    except Exception as e:
        logger.error(f"持仓复盘失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    return ApiResponse(data={"content": result.get("content", "")})
