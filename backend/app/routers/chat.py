"""Chat API — 唯一入口，Prompt 模板 + LLM"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.schemas.common import ApiResponse
from app.schemas.ai import AIAnalysisResponse, PromptTemplateOut, PromptTemplateUpdateIn

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PROMPT = """你是一位资深A股短线交易分析师。用户查询了股票：{{query}}。

请按以下 JSON 格式返回分析结果（不要包含其他内容）：
{
  "stock": {
    "name": "股票名称",
    "code": "股票代码",
    "summary": "一句话概述该股当前状态"
  },
  "market_context": {
    "status": "当前市场情绪判断（冰点/回暖/高潮/退潮）",
    "impact": "市场环境对该股的影响"
  },
  "analysis": {
    "technical": "技术面分析（趋势、关键位置、量价关系）",
    "fundamental": "基本面要点",
    "fund_flow": "资金面分析",
    "catalyst": "近期催化剂或风险事件"
  },
  "risk_assessment": {
    "level": "风险等级（低/中/高）",
    "reasons": ["风险1", "风险2"],
    "support_level": "关键支撑位",
    "resistance_level": "关键压力位"
  },
  "conclusion": "综合结论（不给出买卖建议，仅客观评价）"
}

注意：不给出买卖建议。数据力求准确，不确定的地方如实说明。用中文输出。"""


async def _get_template(db: AsyncSession) -> str:
    """从数据库获取默认 Prompt 模板"""
    row = await db.execute(
        text("SELECT template_content FROM ai_prompt_templates WHERE name='chat_default' LIMIT 1")
    )
    r = row.fetchone()
    if r:
        return r[0]
    # 自动初始化
    await db.execute(
        text("INSERT INTO ai_prompt_templates (name, template_content, is_default) VALUES ('chat_default', :t, 1)"),
        {"t": DEFAULT_PROMPT},
    )
    await db.commit()
    return DEFAULT_PROMPT


from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="股票代码或名称")


@router.post("/chat", response_model=ApiResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """统一 Chat 入口 — 用户输入股票代码/名称 → LLM 返回结构化分析"""
    query = body.query.strip()
    if not query:
        return ApiResponse(code=400, message="请输入股票代码或名称", data=None)

    if not settings.LLM_API_KEY:
        return ApiResponse(code=500, message="未配置 LLM API Key", data={"content": "请在 .env 中设置 LLM_API_KEY"})

    template = await _get_template(db)
    system_prompt = template.replace("{{query}}", query)

    from app.services.llm import chat as llm_chat

    try:
        result = await llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"分析股票：{query}"}
        ])
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Chat 失败: {e}")
        return ApiResponse(code=500, message=f"AI 请求失败：{e}", data=None)


# ---------- 提示词模板管理 ----------

@router.get("/admin/prompt-templates", response_model=ApiResponse[list[PromptTemplateOut]])
async def list_templates(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        text("SELECT id, name, template_content, is_default FROM ai_prompt_templates ORDER BY id")
    )
    templates = []
    for r in rows.fetchall():
        templates.append(PromptTemplateOut(
            id=r[0], name=r[1], template_content=r[2], is_default=bool(r[3]),
        ))
    return ApiResponse(data=templates)


@router.put("/admin/prompt-templates/{template_id}", response_model=ApiResponse[PromptTemplateOut])
async def update_template(template_id: int, body: PromptTemplateUpdateIn, db: AsyncSession = Depends(get_db)):
    row = await db.execute(
        text("SELECT id, name, template_content, is_default FROM ai_prompt_templates WHERE id=:id"),
        {"id": template_id},
    )
    existing = row.fetchone()
    if not existing:
        return ApiResponse(code=404, message="模板不存在", data=None)

    if body.is_default:
        await db.execute(text("UPDATE ai_prompt_templates SET is_default=0"))
        await db.execute(
            text("UPDATE ai_prompt_templates SET template_content=:t, is_default=1 WHERE id=:id"),
            {"t": body.template_content, "id": template_id},
        )
    else:
        await db.execute(
            text("UPDATE ai_prompt_templates SET template_content=:t WHERE id=:id"),
            {"t": body.template_content, "id": template_id},
        )
    await db.commit()

    return ApiResponse(data=PromptTemplateOut(
        id=existing[0], name=existing[1],
        template_content=body.template_content,
        is_default=body.is_default if body.is_default else bool(existing[3]),
    ))
