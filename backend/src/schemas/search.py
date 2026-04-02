from __future__ import annotations

from pydantic import BaseModel, Field


class GlobalSearchResultItem(BaseModel):
    object_type: str = Field(..., description="对象类型")
    object_id: str = Field(..., description="对象ID")
    title: str = Field(..., description="主标题")
    subtitle: str | None = Field(None, description="副标题")
    summary: str | None = Field(None, description="摘要")
    keywords: list[str] = Field(default_factory=list, description="命中的关键字段")
    route_path: str = Field(..., description="前端详情跳转路径")
    score: int = Field(..., ge=0, description="相关度评分")
    business_rank: int = Field(..., ge=0, description="业务置顶权重")
    group_label: str = Field(..., description="对象分组标签")


class GlobalSearchGroup(BaseModel):
    object_type: str = Field(..., description="对象类型")
    label: str = Field(..., description="分组名称")
    count: int = Field(..., ge=0, description="分组结果数")


class GlobalSearchResponse(BaseModel):
    query: str = Field(..., description="搜索词")
    total: int = Field(..., ge=0, description="结果总数")
    items: list[GlobalSearchResultItem] = Field(default_factory=list, description="全部视图结果")
    groups: list[GlobalSearchGroup] = Field(default_factory=list, description="按对象分组结果")
