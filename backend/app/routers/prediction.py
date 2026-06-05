"""AI 预测 API — 个股预测 + 行业预测 + 保存跟踪 + 复盘"""
import json
import logging
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from config import settings
from app.schemas.common import ApiResponse
from app.models.chat_cache import PredictionCache
from app.services.data_engine import fetch_stock_data, fetch_industry_data, get_active_template

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = 1

# ---------- 预测时段映射 ----------

STOCK_HORIZONS = {
    "tomorrow": "个股预测-下一交易日",
    "week": "个股预测-一周",
    "1m": "个股预测-1个月",
    "3m": "个股预测-3个月",
}

STOCK_HORIZON_LABELS = {
    "tomorrow": "下一交易日",
    "week": "未来5个交易日",
    "1m": "未来1个月（约20个交易日）",
    "3m": "未来3个月（约60个交易日）",
}

STOCK_REVIEW_SCENES = {
    "tomorrow": "stock_review_tomorrow",
    "week": "stock_review_week",
    "1m": "stock_review_1m",
    "3m": "stock_review_3m",
}

# ---------- 个股预测 ----------

class StockPredictionRequest(BaseModel):
    code: str = Field(..., description="股票代码或名称")
    horizon: str = Field(..., description="预测时段：tomorrow / week / 1m / 3m")


@router.post("/prediction/stock", response_model=ApiResponse)
async def predict_stock(body: StockPredictionRequest, db: AsyncSession = Depends(get_db)):
    """个股预测 — 数据引擎 + 预测提示词，输出五模块报告（同日同股票同时段缓存）"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    if body.horizon not in STOCK_HORIZONS:
        return ApiResponse(code=400, message=f"无效的预测时段，可选：{', '.join(STOCK_HORIZONS.keys())}", data=None)

    today = date.today()

    # 1. 查同日同股票同时段缓存
    stmt = select(PredictionCache).where(
        PredictionCache.query == body.code,
        PredictionCache.horizon == body.horizon,
        PredictionCache.search_date == today,
    ).limit(1)
    cached = (await db.execute(stmt)).scalar_one_or_none()
    if cached:
        cached_data = json.loads(cached.response)
        cached_data["cached"] = True
        return ApiResponse(data=cached_data)

    # 2. 数据引擎获取数据
    data_result = await fetch_stock_data(body.code, body.code, db)
    confidence = data_result["confidence_label"]

    # 低置信度 → 拒绝生成预测
    if confidence == "低":
        return ApiResponse(code=400, message="当前数据源存在冲突或核心数据缺失，无法生成可靠预测", data={
            "confidence": confidence,
            "data_summary": data_result["structured_data"],
        })

    # 3. 获取预测提示词
    scene = f"stock_prediction_{body.horizon}"
    template = await get_active_template(db, scene)
    if not template:
        return ApiResponse(code=400, message="当前AI模板未配置，请联系管理员", data=None)

    # 4. 注入数据到模板
    horizon_label = STOCK_HORIZON_LABELS[body.horizon]
    data_json = json.dumps(data_result["structured_data"], ensure_ascii=False, indent=2)

    system_prompt = template.replace("{{query}}", body.code)
    system_prompt = system_prompt.replace("{{horizon}}", horizon_label)
    system_prompt = system_prompt.replace("{{data}}", data_json)
    system_prompt = system_prompt.replace("{{confidence}}", confidence)

    # 5. 调 LLM
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"预测股票 {body.code} 在 {horizon_label} 的走势"},
        ])
    except Exception as e:
        logger.error(f"个股预测失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    content = result.get("content", "")

    # 6. 记录调用日志
    await _log_call(db, scene, f"股票:{body.code} 时段:{body.horizon}", content[:200], confidence)

    response_data = {
        "content": content,
        "confidence": confidence,
        "data_snapshot": data_result["structured_data"],
        "source_urls": data_result["source_urls"],
        "fetch_timestamp": data_result["fetch_timestamp"],
    }

    # 7. 写入缓存
    cache_entry = PredictionCache(
        query=body.code,
        horizon=body.horizon,
        response=json.dumps(response_data, ensure_ascii=False),
        search_date=today,
    )
    db.add(cache_entry)
    await db.flush()

    response_data["cached"] = False
    return ApiResponse(data=response_data)


# ---------- 行业预测 ----------

class IndustryPredictionRequest(BaseModel):
    name: str = Field(..., description="行业板块名称")


@router.post("/prediction/industry", response_model=ApiResponse)
async def predict_industry(body: IndustryPredictionRequest, db: AsyncSession = Depends(get_db)):
    """行业预测 — 双时间维度（短期1-3月 + 长期6月+）"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    # 1. 数据引擎获取行业数据
    data_result = await fetch_industry_data(body.name, db)
    confidence = data_result["confidence_label"]

    if confidence == "低":
        return ApiResponse(code=400, message="当前数据源存在冲突或核心数据缺失，无法生成可靠预测", data={
            "confidence": confidence,
            "data_summary": data_result["structured_data"],
        })

    # 2. 获取行业研判提示词
    template = await get_active_template(db, "industry_analysis")
    if not template:
        return ApiResponse(code=400, message="当前AI模板未配置，请联系管理员", data=None)

    # 3. 注入数据
    data_json = json.dumps(data_result["structured_data"], ensure_ascii=False, indent=2)

    system_prompt = template.replace("{{query}}", body.name)
    system_prompt = system_prompt.replace("{{data}}", data_json)
    system_prompt = system_prompt.replace("{{confidence}}", confidence)

    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"研判行业「{body.name}」的短期和长期走势"},
        ])
    except Exception as e:
        logger.error(f"行业预测失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    content = result.get("content", "")

    await _log_call(db, "industry_analysis", f"行业:{body.name}", content[:200], confidence)

    return ApiResponse(data={
        "content": content,
        "confidence": confidence,
        "data_snapshot": data_result["structured_data"],
        "source_urls": data_result["source_urls"],
        "fetch_timestamp": data_result["fetch_timestamp"],
        "cached": False,
    })


# ---------- 保存预测记录并开启跟踪 ----------

class SavePredictionBody(BaseModel):
    type: str = Field(default="stock", description="stock / industry")
    code: str = Field(default="", description="股票代码")
    name: str = Field(..., description="标的名称")
    horizon: str = Field(default="", description="预测时段")
    content: str = Field(..., description="预测报告内容")
    confidence: str = Field(default="", description="置信度标签")
    data_snapshot: dict | None = Field(default=None, description="数据快照")
    source_urls: list[str] | None = Field(default=None, description="数据来源URL")


@router.post("/prediction/save", response_model=ApiResponse)
async def save_prediction(body: SavePredictionBody, db: AsyncSession = Depends(get_db)):
    """保存预测记录并开启跟踪（用户手动确认）"""

    if not body.name or not body.content:
        return ApiResponse(code=400, message="缺少必要参数", data=None)

    # 存储上限检查
    if body.type == "stock":
        count_row = await db.execute(
            text("SELECT COUNT(1) FROM prediction_records WHERE user_id=:uid AND type='stock' AND is_deleted=0"),
            {"uid": DEFAULT_USER_ID},
        )
        if count_row.fetchone()[0] >= 10:
            return ApiResponse(code=400, message="预测记录已达存储上限，请清理无用记录后再新增", data=None)
    elif body.type == "industry":
        count_row = await db.execute(
            text("SELECT COUNT(1) FROM prediction_records WHERE user_id=:uid AND type='industry' AND is_deleted=0"),
            {"uid": DEFAULT_USER_ID},
        )
        if count_row.fetchone()[0] >= 3:
            return ApiResponse(code=400, message="行业预测记录已达存储上限，请清理无用记录后再新增", data=None)

    # 创建预测记录
    new_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        text("""INSERT INTO prediction_records (id, user_id, type, code, name, horizon, prediction_content, confidence_label, status, is_deleted, created_at, updated_at)
                VALUES (:id, :uid, :type, :code, :name, :horizon, :content, :confidence, 'tracking', 0, :now, :now)"""),
        {"id": new_id, "uid": DEFAULT_USER_ID, "type": body.type, "code": body.code, "name": body.name,
         "horizon": body.horizon, "content": body.content, "confidence": body.confidence, "now": now},
    )

    # 创建数据快照
    snapshot_id = str(uuid.uuid4())
    await db.execute(
        text("""INSERT INTO data_snapshots (id, prediction_id, structured_data, source_urls, fetch_timestamp, confidence_label)
                VALUES (:id, :pid, :sdata, :surls, :now, :conf)"""),
        {"id": snapshot_id, "pid": new_id,
         "sdata": json.dumps(body.data_snapshot or {}, ensure_ascii=False),
         "surls": json.dumps(body.source_urls or [], ensure_ascii=False),
         "now": now, "conf": body.confidence},
    )

    await db.flush()

    return ApiResponse(data={"id": new_id, "status": "tracking"})


# ---------- 预测记录列表 ----------

@router.get("/prediction/records", response_model=ApiResponse)
async def list_predictions(
    type: str = Query(None, description="stock / industry"),
    db: AsyncSession = Depends(get_db),
):
    """获取预测记录列表"""
    conditions = ["user_id = :uid", "is_deleted = 0"]
    params = {"uid": DEFAULT_USER_ID}

    if type:
        conditions.append("type = :type")
        params["type"] = type

    where = " AND ".join(conditions)

    rows = await db.execute(
        text(f"""SELECT id, type, code, name, horizon, prediction_content, confidence_label, status, created_at
                FROM prediction_records WHERE {where} ORDER BY created_at DESC"""),
        params,
    )
    items = []
    for r in rows.fetchall():
        items.append({
            "id": r[0], "type": r[1], "code": r[2], "name": r[3],
            "horizon": r[4], "prediction_content": r[5],
            "confidence_label": r[6], "status": r[7],
            "created_at": str(r[8]) if r[8] else None,
        })

    return ApiResponse(data=items)


@router.get("/prediction/records/{prediction_id}", response_model=ApiResponse)
async def get_prediction_detail(prediction_id: str, db: AsyncSession = Depends(get_db)):
    """获取预测详情（含数据快照 + 复盘记录）"""
    row = await db.execute(
        text("""SELECT id, type, code, name, horizon, prediction_content, confidence_label, status, created_at
                FROM prediction_records WHERE id=:id AND user_id=:uid AND is_deleted=0"""),
        {"id": prediction_id, "uid": DEFAULT_USER_ID},
    )
    r = row.fetchone()
    if not r:
        return ApiResponse(code=404, message="预测记录不存在", data=None)

    # 数据快照
    snap_row = await db.execute(
        text("SELECT structured_data, source_urls, fetch_timestamp, confidence_label FROM data_snapshots WHERE prediction_id=:pid LIMIT 1"),
        {"pid": prediction_id},
    )
    snap = snap_row.fetchone()
    data_snapshot = None
    if snap:
        try:
            data_snapshot = json.loads(snap[0])
        except (json.JSONDecodeError, TypeError):
            data_snapshot = {}
        data_snapshot["_source_urls"] = json.loads(snap[1]) if snap[1] else []
        data_snapshot["_fetch_timestamp"] = str(snap[2]) if snap[2] else ""
        data_snapshot["_confidence"] = snap[3] or ""

    # 复盘记录
    review_rows = await db.execute(
        text("""SELECT id, review_type, accuracy_rating, deviation_reason, review_content, created_at
                FROM review_records WHERE prediction_id=:pid ORDER BY created_at DESC"""),
        {"pid": prediction_id},
    )
    reviews = []
    for rv in review_rows.fetchall():
        reviews.append({
            "id": rv[0], "review_type": rv[1], "accuracy_rating": rv[2],
            "deviation_reason": rv[3], "review_content": rv[4],
            "created_at": str(rv[5]) if rv[5] else None,
        })

    return ApiResponse(data={
        "id": r[0], "type": r[1], "code": r[2], "name": r[3],
        "horizon": r[4], "prediction_content": r[5],
        "confidence_label": r[6], "status": r[7],
        "created_at": str(r[8]) if r[8] else None,
        "data_snapshot": data_snapshot,
        "reviews": reviews,
    })


@router.delete("/prediction/records/{prediction_id}", response_model=ApiResponse)
async def delete_prediction(prediction_id: str, db: AsyncSession = Depends(get_db)):
    """删除预测记录（软删除）"""
    row = await db.execute(
        text("SELECT 1 FROM prediction_records WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": prediction_id, "uid": DEFAULT_USER_ID},
    )
    if not row.fetchone():
        return ApiResponse(code=404, message="预测记录不存在", data=None)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        text("UPDATE prediction_records SET is_deleted=1, updated_at=:now WHERE id=:id"),
        {"now": now, "id": prediction_id},
    )
    await db.flush()
    return ApiResponse(data={"deleted": True})


# ---------- 手动触发复盘 ----------

@router.post("/prediction/records/{prediction_id}/review", response_model=ApiResponse)
async def trigger_review(prediction_id: str, db: AsyncSession = Depends(get_db)):
    """手动触发复盘"""
    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data=None)

    row = await db.execute(
        text("SELECT id, type, code, name, horizon, prediction_content, confidence_label FROM prediction_records WHERE id=:id AND user_id=:uid AND is_deleted=0"),
        {"id": prediction_id, "uid": DEFAULT_USER_ID},
    )
    r = row.fetchone()
    if not r:
        return ApiResponse(code=404, message="预测记录不存在", data=None)

    pred_type = r[1]
    name = r[3]
    horizon = r[4]
    pred_content = r[5]

    # 确定复盘场景
    if pred_type == "stock":
        scene = STOCK_REVIEW_SCENES.get(horizon, "stock_review_tomorrow")
    else:
        scene = "industry_review"

    template = await get_active_template(db, scene)
    if not template:
        return ApiResponse(code=400, message="当前AI模板未配置，请联系管理员", data=None)

    # 获取最新数据
    if pred_type == "stock":
        data_result = await fetch_stock_data(r[2], name, db)
    else:
        data_result = await fetch_industry_data(name, db)

    current_data = json.dumps(data_result["structured_data"], ensure_ascii=False, indent=2)

    system_prompt = template.replace("{{prediction}}", pred_content[:3000])
    system_prompt = system_prompt.replace("{{current_data}}", current_data)

    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"复盘 {name} 的预测"},
        ])
    except Exception as e:
        logger.error(f"复盘失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    review_content = result.get("content", "")

    # 保存复盘记录
    review_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    review_type = scene

    await db.execute(
        text("""INSERT INTO review_records (id, prediction_id, review_type, accuracy_rating, deviation_reason, review_content, created_at)
                VALUES (:id, :pid, :rtype, '', '', :content, :now)"""),
        {"id": review_id, "pid": prediction_id, "rtype": review_type, "content": review_content, "now": now},
    )
    await db.flush()

    return ApiResponse(data={
        "id": review_id,
        "review_type": review_type,
        "content": review_content,
    })


# ---------- 辅助函数 ----------

async def _log_call(db: AsyncSession, scene: str, input_summary: str, output_summary: str, confidence: str):
    """记录 LLM 调用日志"""
    try:
        log_id = str(uuid.uuid4())
        await db.execute(
            text("""INSERT INTO ai_call_logs (id, template_id, scene, input_summary, output_summary, confidence_label, created_at)
                    VALUES (:id, '', :scene, :inp, :out, :conf, datetime('now', 'localtime'))"""),
            {"id": log_id, "scene": scene, "inp": input_summary[:200], "out": output_summary[:200], "conf": confidence},
        )
        await db.flush()
    except Exception as e:
        logger.warning(f"调用日志写入失败: {e}")
