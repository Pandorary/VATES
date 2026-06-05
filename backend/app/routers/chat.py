"""Chat API + Prompt 模板 CRUD"""
import logging
import uuid
from datetime import datetime, date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from config import settings
from app.schemas.common import ApiResponse
from app.schemas.ai import (
    PromptTemplateOut,
    PromptTemplateCreateIn,
    PromptTemplateUpdateIn,
    PromptTemplateListOut,
)
from app.models.chat_cache import AIChatCache

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_active_template(db: AsyncSession, scene: str = "stock_analysis") -> str | None:
    """按 scene 获取启用的提示词（兼容旧 skill 字段）"""
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE scene=:scene AND is_active=1 AND is_deleted=0 LIMIT 1"),
        {"scene": scene},
    )
    r = row.fetchone()
    if r:
        return r[0]
    # 兼容旧数据：按 skill 字段查找
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE skill=:skill AND is_active=1 AND is_deleted=0 LIMIT 1"),
        {"skill": scene},
    )
    r = row.fetchone()
    return r[0] if r else None


# ---------- Chat ----------


class ChatRequest(BaseModel):
    query: str = Field(..., description="股票代码或名称")


@router.post("/chat", response_model=ApiResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """统一 Chat 入口（同一天同一只股票缓存）"""
    query = body.query.strip()
    if not query:
        return ApiResponse(code=400, message="请输入股票代码或名称", data=None)

    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data={"content": "请在 .env 中设置 LLM_API_KEY"})

    today = date.today()

    # 1. 查缓存
    stmt = select(AIChatCache).where(
        AIChatCache.query == query,
        AIChatCache.search_date == today,
    ).limit(1)
    cached = (await db.execute(stmt)).scalar_one_or_none()
    if cached:
        return ApiResponse(data={"content": cached.response, "cached": True})

    # 2. 取模板
    template = await _get_active_template(db)
    if not template:
        return ApiResponse(code=400, message="未找到可用的提示词模板，请在提示词管理中创建并启用 stock_analysis 模板", data=None)
    system_prompt = template.replace("{{query}}", query)

    # 3. 调 LLM
    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析股票：{query}"},
        ])
    except Exception as e:
        logger.error(f"Chat 失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)

    # 4. 写入缓存
    content = result.get("content", "")
    cache_entry = AIChatCache(
        query=query, response=content, search_date=today,
    )
    db.add(cache_entry)
    await db.flush()

    return ApiResponse(data={"content": content, "cached": False})


# ---------- Prompt 模板 CRUD ----------

ADMIN = "admin"
SELECT_COLS = "id, scene, role, role_name, module, skill, skill_summary, skill_detail, is_active, created_at, created_by, updated_at, updated_by"

# 业务场景定义
SCENES = [
    "content_classify",        # 内容智能分类
    "data_extraction",         # 数据提取与校验
    "stock_prediction_tomorrow",  # 个股预测-下一交易日
    "stock_prediction_week",      # 个股预测-一周
    "stock_prediction_1m",        # 个股预测-1个月
    "stock_prediction_3m",        # 个股预测-3个月
    "industry_analysis",          # 行业研判
    "stock_review_tomorrow",      # 个股复盘-下一交易日
    "stock_review_week",          # 个股复盘-一周
    "stock_review_1m",            # 个股复盘-1个月
    "stock_review_3m",            # 个股复盘-3个月
    "industry_review",            # 行业复盘校验
    "position_diagnosis",         # 持仓智能诊断
    "position_review",            # 持仓复盘校验
]

SCENE_LABELS = {
    "content_classify": "内容智能分类",
    "data_extraction": "数据提取与校验",
    "stock_prediction_tomorrow": "个股预测-下一交易日",
    "stock_prediction_week": "个股预测-一周",
    "stock_prediction_1m": "个股预测-1个月",
    "stock_prediction_3m": "个股预测-3个月",
    "industry_analysis": "行业研判",
    "stock_review_tomorrow": "个股复盘-下一交易日",
    "stock_review_week": "个股复盘-一周",
    "stock_review_1m": "个股复盘-1个月",
    "stock_review_3m": "个股复盘-3个月",
    "industry_review": "行业复盘校验",
    "position_diagnosis": "持仓智能诊断",
    "position_review": "持仓复盘校验",
}


def _row_to_out(r) -> PromptTemplateOut:
    return PromptTemplateOut(
        id=r[0], scene=r[1] or "", role=r[2] or "", role_name=r[3] or "",
        module=r[4] or "",
        skill=r[5] or "", skill_summary=r[6] or "", skill_detail=r[7] or "",
        is_active=bool(r[8]),
        created_at=str(r[9]) if r[9] else None,
        created_by=r[10] or "",
        updated_at=str(r[11]) if r[11] else None,
        updated_by=r[12] or "",
    )


async def _get_active_template_by_scene(db: AsyncSession, scene: str) -> str | None:
    """获取指定场景的激活模板内容"""
    row = await db.execute(
        text("SELECT skill_detail FROM ai_prompts WHERE scene=:scene AND is_active=1 AND is_deleted=0 LIMIT 1"),
        {"scene": scene},
    )
    r = row.fetchone()
    return r[0] if r else None


@router.get("/admin/prompt-templates/scenes", response_model=ApiResponse)
async def list_scenes():
    """获取所有业务场景列表"""
    scenes = [{"code": k, "label": v} for k, v in SCENE_LABELS.items()]
    return ApiResponse(data=scenes)


@router.get("/admin/prompt-templates", response_model=ApiResponse[PromptTemplateListOut])
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    scene: str | None = None,
    role: str | None = None,
    module: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """分页查询提示词模板"""
    conditions = ["is_deleted = 0"]
    params: dict = {}

    if scene:
        conditions.append("scene = :scene")
        params["scene"] = scene
    if role:
        conditions.append("role_name = :role")
        params["role"] = role
    if module:
        conditions.append("module = :module")
        params["module"] = module
    if search:
        conditions.append("(role_name LIKE :search OR skill_summary LIKE :search2)")
        params["search"] = f"%{search}%"
        params["search2"] = f"%{search}%"

    where = " AND ".join(conditions)

    count_row = await db.execute(
        text(f"SELECT COUNT(1) FROM ai_prompts WHERE {where}"), params
    )
    total = count_row.fetchone()[0]

    rows = await db.execute(
        text(f"""SELECT {SELECT_COLS} FROM ai_prompts
                WHERE {where} ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset"""),
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    items = [_row_to_out(r) for r in rows.fetchall()]
    return ApiResponse(data=PromptTemplateListOut(items=items, total=total, page=page, page_size=page_size))


@router.get("/admin/prompt-templates/{template_id}", response_model=ApiResponse[PromptTemplateOut])
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text(f"SELECT {SELECT_COLS} FROM ai_prompts WHERE id=:id AND is_deleted=0"),
        {"id": template_id},
    )
    r = row.fetchone()
    if not r:
        return ApiResponse(code=404, message="模板不存在", data=None)
    return ApiResponse(data=_row_to_out(r))


@router.post("/admin/prompt-templates", response_model=ApiResponse[PromptTemplateOut])
async def create_template(body: PromptTemplateCreateIn, db: AsyncSession = Depends(get_db)):
    if not body.role_name.strip():
        return ApiResponse(code=400, message="角色名称不能为空", data=None)
    if not body.scene.strip():
        return ApiResponse(code=400, message="业务场景不能为空", data=None)

    new_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 如果新模板设为激活，先停用同场景其他模板
    await db.execute(
        text("""INSERT INTO ai_prompts (id, scene, role, role_name, module, skill, skill_summary, skill_detail, is_active, is_deleted,
                       created_at, created_by, updated_at, updated_by)
                VALUES (:id, :scene, :role, :role_name, :module, :skill, :skill_summary, :skill_detail, 1, 0, :now, :by, :now, :by)"""),
        {"id": new_id, "scene": body.scene, "role": body.role, "role_name": body.role_name,
         "module": body.module,
         "skill": body.skill, "skill_summary": body.skill_summary, "skill_detail": body.skill_detail,
         "now": now, "by": ADMIN},
    )
    # 唯一激活规则：停用同场景其他模板
    await db.execute(
        text("UPDATE ai_prompts SET is_active=0, updated_at=:now WHERE scene=:scene AND id != :id AND is_active=1 AND is_deleted=0"),
        {"scene": body.scene, "id": new_id, "now": now},
    )
    await db.flush()

    return ApiResponse(data=PromptTemplateOut(
        id=new_id, scene=body.scene, role=body.role, role_name=body.role_name,
        module=body.module,
        skill=body.skill, skill_summary=body.skill_summary, skill_detail=body.skill_detail,
        is_active=True, created_at=now, created_by=ADMIN, updated_at=now, updated_by=ADMIN,
    ))


@router.put("/admin/prompt-templates/{template_id}", response_model=ApiResponse[PromptTemplateOut])
async def update_template(template_id: str, body: PromptTemplateUpdateIn, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text(f"SELECT {SELECT_COLS} FROM ai_prompts WHERE id=:id AND is_deleted=0"),
        {"id": template_id},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="模板不存在", data=None)

    vals = {
        "scene": body.scene if body.scene is not None else (existing[1] or ""),
        "role": body.role if body.role is not None else (existing[2] or ""),
        "role_name": body.role_name if body.role_name is not None else (existing[3] or ""),
        "module": body.module if body.module is not None else (existing[4] or ""),
        "skill": body.skill if body.skill is not None else (existing[5] or ""),
        "skill_summary": body.skill_summary if body.skill_summary is not None else (existing[6] or ""),
        "skill_detail": body.skill_detail if body.skill_detail is not None else (existing[7] or ""),
        "active": body.is_active if body.is_active is not None else bool(existing[8]),
    }
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 如果设为激活，停用同场景其他模板
    if vals["active"]:
        await db.execute(
            text("UPDATE ai_prompts SET is_active=0, updated_at=:now WHERE scene=:scene AND id != :id AND is_active=1 AND is_deleted=0"),
            {"scene": vals["scene"], "id": template_id, "now": now},
        )

    await db.execute(
        text("""UPDATE ai_prompts
                SET scene=:scene, role=:role, role_name=:role_name, module=:module, skill=:skill, skill_summary=:skill_summary,
                    skill_detail=:skill_detail, is_active=:active, updated_at=:now, updated_by=:by
                WHERE id=:id"""),
        {**vals, "now": now, "by": ADMIN, "id": template_id},
    )
    await db.flush()

    return ApiResponse(data=PromptTemplateOut(
        id=existing[0], scene=vals["scene"], role=vals["role"], role_name=vals["role_name"],
        module=vals["module"],
        skill=vals["skill"], skill_summary=vals["skill_summary"], skill_detail=vals["skill_detail"],
        is_active=vals["active"],
        created_at=str(existing[9]) if existing[9] else None,
        created_by=existing[10] or "",
        updated_at=now, updated_by=ADMIN,
    ))


@router.delete("/admin/prompt-templates/{template_id}", response_model=ApiResponse)
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text(f"SELECT is_active FROM ai_prompts WHERE id=:id AND is_deleted=0"),
        {"id": template_id},
    )
    r = row.fetchone()
    if not r:
        return ApiResponse(code=404, message="模板不存在", data=None)
    if bool(r[0]):
        return ApiResponse(code=400, message="激活状态的模板不可删除，请先停用", data=None)

    await db.execute(
        text("UPDATE ai_prompts SET is_deleted=1, updated_at=:now, updated_by=:by WHERE id=:id"),
        {"now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "by": ADMIN, "id": template_id},
    )
    await db.flush()
    return ApiResponse(data={"deleted": True})


@router.post("/admin/prompt-templates/{template_id}/copy", response_model=ApiResponse[PromptTemplateOut])
async def copy_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """复制模板"""
    row = await db.execute(
        text(f"SELECT {SELECT_COLS} FROM ai_prompts WHERE id=:id AND is_deleted=0"),
        {"id": template_id},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="模板不存在", data=None)

    new_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        text("""INSERT INTO ai_prompts (id, scene, role, role_name, module, skill, skill_summary, skill_detail, is_active, is_deleted,
                       created_at, created_by, updated_at, updated_by)
                VALUES (:id, :scene, :role, :role_name, :module, :skill, :skill_summary, :skill_detail, 0, 0, :now, :by, :now, :by)"""),
        {"id": new_id, "scene": existing[1] or "", "role": existing[2] or "", "role_name": existing[3] or "" + " (副本)",
         "module": existing[4] or "",
         "skill": existing[5] or "", "skill_summary": existing[6] or "", "skill_detail": existing[7] or "",
         "now": now, "by": ADMIN},
    )
    await db.flush()

    return ApiResponse(data=PromptTemplateOut(
        id=new_id, scene=existing[1] or "", role=existing[2] or "", role_name=existing[3] or "" + " (副本)",
        module=existing[4] or "",
        skill=existing[5] or "", skill_summary=existing[6] or "", skill_detail=existing[7] or "",
        is_active=False, created_at=now, created_by=ADMIN, updated_at=now, updated_by=ADMIN,
    ))
