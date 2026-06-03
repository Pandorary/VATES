"""AI 相关 schemas"""
from pydantic import BaseModel, Field


class PromptTemplateOut(BaseModel):
    id: str
    scene: str
    role: str
    role_name: str
    module: str
    skill: str
    skill_summary: str
    skill_detail: str
    is_active: bool
    created_at: str | None = None
    created_by: str
    updated_at: str | None = None
    updated_by: str

    class Config:
        from_attributes = True


class PromptTemplateCreateIn(BaseModel):
    scene: str = Field(default="", description="业务场景编码")
    role: str = Field(default="", description="角色编码")
    role_name: str = Field(default="", description="角色名称")
    module: str = Field(default="", description="功能模块编码")
    skill: str = Field(default="", description="技能编码")
    skill_summary: str = Field(default="", description="技能名称")
    skill_detail: str = Field(default="", description="技能详细描述")


class PromptTemplateUpdateIn(BaseModel):
    scene: str | None = None
    role: str | None = None
    role_name: str | None = None
    module: str | None = None
    skill: str | None = None
    skill_summary: str | None = None
    skill_detail: str | None = None
    is_active: bool | None = None


class PromptTemplateListOut(BaseModel):
    items: list[PromptTemplateOut]
    total: int
    page: int
    page_size: int
