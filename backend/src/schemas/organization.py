from typing import Any

"""
组织架构相关数据验证模式

注意：组织类型和状态字段已使用 str 类型，业务规则验证由 Service 层处理
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import attributes as orm_attributes

from ..models.organization import RepresentedPartyPerspective


def _validate_represented_party_pair(
    represented_party_id: str | None,
    represented_party_perspective: RepresentedPartyPerspective | None,
) -> None:
    if (represented_party_id is None) != (represented_party_perspective is None):
        raise ValueError(
            "represented_party_id 与 represented_party_perspective 必须同时为空或同时有值"
        )


class RepresentingOrganizationItem(BaseModel):
    """代表指定主体（Party）的组织只读摘要（主体详情反向列表用）"""

    organization_id: str = Field(..., description="组织ID")
    name: str = Field(..., description="组织名称")
    code: str = Field(..., description="组织编码")
    level: int = Field(..., description="组织层级")
    status: str = Field(..., description="组织状态")
    parent_id: str | None = Field(None, description="上级组织ID")
    represented_party_perspective: RepresentedPartyPerspective | None = Field(
        None, description="代表视角（owner/manager）"
    )


class OrganizationBase(BaseModel):
    """组织架构基础模式"""

    name: str = Field(..., min_length=1, max_length=200, description="组织名称")
    code: str = Field(..., min_length=1, max_length=50, description="组织编码")
    level: int = Field(default=1, ge=1, le=10, description="组织层级")
    sort_order: int = Field(default=0, ge=0, description="排序")
    parent_id: str | None = Field(None, description="上级组织ID")

    # 组织基本信息
    type: str = Field(..., description="组织类型")
    status: str = Field(..., description="状态")

    # 其他信息
    description: str | None = Field(None, max_length=1000, description="组织描述")


class OrganizationCreate(OrganizationBase):
    """创建组织架构模式"""

    created_by: str | None = Field(None, max_length=100, description="创建人")

    model_config = ConfigDict(extra="forbid")


class OrganizationUpdate(BaseModel):
    """更新组织架构模式"""

    name: str | None = Field(None, min_length=1, max_length=200, description="组织名称")
    code: str | None = Field(None, min_length=1, max_length=50, description="组织编码")
    level: int | None = Field(None, ge=1, le=10, description="组织层级")
    sort_order: int | None = Field(None, ge=0, description="排序")
    # 组织基本信息
    type: str | None = Field(None, description="组织类型")
    status: str | None = Field(None, description="状态")

    # 其他信息
    description: str | None = Field(None, max_length=1000, description="组织描述")

    updated_by: str | None = Field(None, max_length=100, description="更新人")

    model_config = ConfigDict(extra="forbid")


class OrganizationResponse(OrganizationBase):
    """组织架构响应模式"""

    id: str
    path: str | None = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None
    represented_party_id: str | None = None
    represented_party_perspective: RepresentedPartyPerspective | None = None

    # 子组织列表
    children: list["OrganizationResponse"] | None = []

    @model_validator(mode="before")
    @classmethod
    def coerce_organization_model(cls, v: Any) -> Any:
        """避免在响应序列化中触发 children 懒加载。"""
        if isinstance(v, dict):
            return v
        try:
            state = sa_inspect(v)
        except Exception:
            return v

        data = {attr.key: getattr(v, attr.key) for attr in state.mapper.column_attrs}

        try:
            children_state = state.attrs.children
            children_value = children_state.loaded_value
            no_value = getattr(orm_attributes, "NO_VALUE", None)
            data["children"] = [] if children_value is no_value else children_value
        except Exception:
            data["children"] = []

        return data

    model_config = ConfigDict(from_attributes=True)


class OrganizationPartyScopeProposal(BaseModel):
    """The only write proposal for an Organization's represented Party."""

    represented_party_id: str | None = Field(
        ..., description="Approved active legal Party ID, or null to inherit"
    )
    represented_party_perspective: RepresentedPartyPerspective | None = Field(
        ..., description="owner or manager, or null to inherit"
    )

    @model_validator(mode="after")
    def validate_represented_party_pair(self) -> "OrganizationPartyScopeProposal":
        _validate_represented_party_pair(
            self.represented_party_id,
            self.represented_party_perspective,
        )
        return self

    model_config = ConfigDict(extra="forbid")


class OrganizationPartyScopeState(BaseModel):
    """Direct link and effective inherited scope for one Organization."""

    represented_party_id: str | None = None
    represented_party_perspective: RepresentedPartyPerspective | None = None
    effective_party_id: str | None = None
    effective_party_perspective: RepresentedPartyPerspective | None = None
    source_organization_id: str | None = None


class OrganizationPartyScopeImpact(BaseModel):
    """Counts affected by an Organization represented-Party change."""

    organization_count: int = Field(..., ge=0)
    organization_scope_change_count: int = Field(..., ge=0)
    user_count: int = Field(..., ge=0)
    user_scope_change_count: int = Field(..., ge=0)


class OrganizationPartyScopePreviewResponse(BaseModel):
    organization_id: str
    before_scope: OrganizationPartyScopeState
    after_scope: OrganizationPartyScopeState
    impact: OrganizationPartyScopeImpact
    preview_token: str
    expires_at: datetime


class OrganizationPartyScopeCommitRequest(BaseModel):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @field_validator("preview_token", "reason", "idempotency_key")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class OrganizationPartyScopeCommitResponse(BaseModel):
    organization: OrganizationResponse
    before_scope: OrganizationPartyScopeState
    after_scope: OrganizationPartyScopeState
    impact: OrganizationPartyScopeImpact
    committed_at: datetime
    idempotent: bool = False


class OrganizationPartyScopeBatchProposal(OrganizationPartyScopeProposal):
    """One direct Organization Party scope proposal inside a batch."""

    organization_id: str = Field(..., min_length=1, max_length=100)

    @field_validator("organization_id")
    @classmethod
    def normalize_organization_id(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("organization_id must not be blank")
        return normalized


class OrganizationPartyScopeBatchPreviewRequest(BaseModel):
    items: list[OrganizationPartyScopeBatchProposal] = Field(
        ..., min_length=2, max_length=100
    )

    @model_validator(mode="after")
    def reject_duplicate_organizations(
        self,
    ) -> "OrganizationPartyScopeBatchPreviewRequest":
        organization_ids = [item.organization_id for item in self.items]
        if len(set(organization_ids)) != len(organization_ids):
            raise ValueError("organization_id must be unique within a batch")
        return self

    model_config = ConfigDict(extra="forbid")


class OrganizationPartyScopeBatchPreviewItem(BaseModel):
    organization: OrganizationResponse
    before_scope: OrganizationPartyScopeState
    after_scope: OrganizationPartyScopeState
    impact: OrganizationPartyScopeImpact


class OrganizationPartyScopeBatchPreviewResponse(BaseModel):
    items: list[OrganizationPartyScopeBatchPreviewItem]
    impact: OrganizationPartyScopeImpact
    preview_token: str
    expires_at: datetime


class OrganizationPartyScopeBatchCommitRequest(OrganizationPartyScopeCommitRequest):
    """Confirmation request for a previously generated batch preview."""


class OrganizationPartyScopeBatchCommitResponse(BaseModel):
    items: list[OrganizationPartyScopeBatchPreviewItem]
    impact: OrganizationPartyScopeImpact
    committed_at: datetime
    idempotent: bool = False


class OrganizationMoveProposal(BaseModel):
    """The only write proposal for an Organization hierarchy move."""

    target_parent_id: str | None = Field(
        ..., description="Target parent Organization ID, or null to become a root"
    )

    @field_validator("target_parent_id")
    @classmethod
    def normalize_target_parent_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized == "":
            raise ValueError("target_parent_id must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class OrganizationMoveScopeState(BaseModel):
    """Effective Party scope at the root of a proposed Organization move."""

    parent_id: str | None = None
    effective_party_id: str | None = None
    effective_party_perspective: RepresentedPartyPerspective | None = None
    source_organization_id: str | None = None


class OrganizationMoveImpact(BaseModel):
    """Counts affected by an Organization hierarchy move."""

    organization_count: int = Field(..., ge=0)
    organization_scope_change_count: int = Field(..., ge=0)
    organization_path_change_count: int = Field(..., ge=0)
    user_count: int = Field(..., ge=0)
    user_scope_change_count: int = Field(..., ge=0)


class OrganizationMovePreviewResponse(BaseModel):
    organization_id: str
    before_scope: OrganizationMoveScopeState
    after_scope: OrganizationMoveScopeState
    impact: OrganizationMoveImpact
    preview_token: str
    expires_at: datetime


class OrganizationMoveCommitRequest(BaseModel):
    preview_token: str = Field(..., min_length=1, max_length=512)
    reason: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @field_validator("preview_token", "reason", "idempotency_key")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        normalized = value.strip()
        if normalized == "":
            raise ValueError("value must not be blank")
        return normalized

    model_config = ConfigDict(extra="forbid")


class OrganizationMoveCommitResponse(BaseModel):
    organization: OrganizationResponse
    before_scope: OrganizationMoveScopeState
    after_scope: OrganizationMoveScopeState
    impact: OrganizationMoveImpact
    committed_at: datetime
    idempotent: bool = False


class OrganizationTree(BaseModel):
    """组织架构树形结构"""

    id: str
    name: str
    code: str
    level: int
    sort_order: int
    type: str
    status: str
    children: list["OrganizationTree"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OrganizationHistoryResponse(BaseModel):
    """组织架构历史响应模式"""

    id: str
    organization_id: str
    action: str
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    change_reason: str | None = None
    created_at: datetime
    created_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationStatistics(BaseModel):
    """组织架构统计信息"""

    total: int = Field(..., description="总数")
    active: int = Field(..., description="活跃数量")
    inactive: int = Field(..., description="非活跃数量")
    by_type: dict[str, Any] = Field(..., description="按类型统计")
    by_level: dict[str, Any] = Field(..., description="按层级统计")


class OrganizationSearchRequest(BaseModel):
    """组织搜索请求"""

    keyword: str | None = Field(None, description="关键词")
    level: int | None = Field(None, ge=1, le=10, description="层级")
    parent_id: str | None = Field(None, description="上级组织ID")
    skip: int = Field(0, ge=0, description="跳过数量")
    page_size: int = Field(100, ge=1, le=1000, description="每页大小")


# 更新前向引用
OrganizationResponse.model_rebuild()
OrganizationTree.model_rebuild()
