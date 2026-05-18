"""AI 相关 schemas"""
from pydantic import BaseModel, Field


class AIAnalysisRequest(BaseModel):
    prompt: str = Field(default="", description="用户补充提示词，留空使用默认分析")
    model: str | None = Field(default=None, description="覆盖默认模型")


class AIAnalysisResponse(BaseModel):
    content: str = Field(..., description="AI 分析结果 (Markdown)")
    model: str = ""
    usage: dict = Field(default_factory=dict, description="token 用量")


class PromptTemplateOut(BaseModel):
    id: int
    name: str
    template_content: str
    is_default: bool


class PromptTemplateUpdateIn(BaseModel):
    template_content: str = Field(..., description="新的模板内容，支持占位符 {{stock_name}} 等")
    is_default: bool | None = None
