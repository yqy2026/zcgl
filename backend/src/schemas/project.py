"""
项目管理相关数据模式
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import attributes as orm_attributes

if TYPE_CHECKING:
    from .asset import AssetListItemResponse

# project_code 格式：PRJ-<SEGMENT>-<SERIAL>
_PROJECT_CODE_PATTERN = re.compile(r"^PRJ-[A-Z0-9]{4,12}-\d{6}$")

_VALID_STATUSES = {"planning", "active", "paused", "completed", "terminated"}


class ProjectBase(BaseModel):
    """项目基础模式（仅包含规格 §3.2 冻结字段）。"""

    project_name: str = Field(..., title="项目名称", min_length=1, max_length=200)
    project_code: str | None = Field(
        None, title="项目编码", min_length=1, max_length=100
    )
    status: str = Field("planning", title="业务状态", max_length=20)
    manager_party_id: str | None = Field(None, title="运营管理主体ID")
    data_status: str = Field("正常", title="数据状态", max_length=20)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_STATUSES:
            raise PydanticCustomError(
                "invalid_project_status",
                f"项目状态必须为 {sorted(_VALID_STATUSES)} 之一",
                {},
            )
        return v


class ProjectPartyRelationInput(BaseModel):
    """项目主体关系入参（当前仅支持 owner 关系）。"""

    party_id: str = Field(..., title="主体ID", min_length=1)
    relation_type: str = Field("owner", title="关系类型", max_length=20)
    is_primary: bool = Field(True, title="是否主关系")
    is_active: bool = Field(True, title="是否生效")

    @field_validator("party_id")
    @classmethod
    def validate_party_id(cls, v: str) -> str:
        party_id = v.strip()
        if party_id == "":
            raise PydanticCustomError(
                "invalid_party_id",
                "主体ID不能为空",
                {},
            )
        return party_id

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: str) -> str:
        relation_type = v.strip()
        if relation_type != "owner":
            raise PydanticCustomError(
                "invalid_relation_type",
                "当前仅支持 owner 关系类型",
                {},
            )
        return relation_type


class ProjectCreate(ProjectBase):
    """创建项目模式"""

    party_relations: list[ProjectPartyRelationInput] | None = Field(
        None, title="主体关系"
    )
    organization_id: str | None = Field(
        None, title="关联组织ID（用于推断 manager_party_id）"
    )

    @field_validator("project_code")
    @classmethod
    def validate_project_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not _PROJECT_CODE_PATTERN.match(v):
            raise PydanticCustomError(
                "invalid_project_code",
                "项目编码格式必须为 PRJ-<4-12位大写字母数字>-<6位序号>，例如: PRJ-ABCD01-000001",
                {},
            )
        return v


class ProjectUpdate(BaseModel):
    """更新项目模式（所有字段可选）。"""

    project_name: str | None = Field(
        None, title="项目名称", min_length=1, max_length=200
    )
    project_code: str | None = Field(
        None, title="项目编码", min_length=1, max_length=100
    )
    status: str | None = Field(None, title="业务状态", max_length=20)
    manager_party_id: str | None = Field(None, title="运营管理主体ID")
    data_status: str | None = Field(None, title="数据状态", max_length=20)
    party_relations: list[ProjectPartyRelationInput] | None = Field(
        None, title="主体关系"
    )

    @field_validator("project_code")
    @classmethod
    def validate_project_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not _PROJECT_CODE_PATTERN.match(v):
            raise PydanticCustomError(
                "invalid_project_code",
                "项目编码格式必须为 PRJ-<4-12位大写字母数字>-<6位序号>，例如: PRJ-ABCD01-000001",
                {},
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _VALID_STATUSES:
            raise PydanticCustomError(
                "invalid_project_status",
                f"项目状态必须为 {sorted(_VALID_STATUSES)} 之一",
                {},
            )
        return v


class ProjectResponse(ProjectBase):
    """项目响应模式。"""

    id: str
    data_status: str
    review_status: str
    review_by: str | None = None
    reviewed_at: datetime | None = None
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None
    asset_count: int = 0
    party_relations: list[dict[str, Any]] = Field(
        default_factory=list, title="主体关系"
    )

    @staticmethod
    def _convert_relation_object_to_dict(relation: Any) -> dict[str, Any]:
        relation_dict = {
            "id": getattr(relation, "id", None),
            "project_id": getattr(relation, "project_id", None),
            "ownership_id": getattr(relation, "ownership_id", None),
            "is_active": getattr(relation, "is_active", True),
            "created_at": getattr(relation, "created_at", None),
            "updated_at": getattr(relation, "updated_at", None),
        }
        ownership = getattr(relation, "ownership", None)
        if ownership is not None:
            relation_dict["ownership_name"] = getattr(
                ownership, "project_name", None
            ) or getattr(ownership, "name", None)
            relation_dict["ownership_code"] = getattr(
                ownership, "project_code", None
            ) or getattr(ownership, "code", None)
        return relation_dict

    @classmethod
    def _serialize_ownership_relations(cls, v: Any) -> list[dict[str, Any]]:
        if v is None:
            return []
        if isinstance(v, dict) or not hasattr(v, "__iter__"):
            return []

        result: list[dict[str, Any]] = []
        for relation in v:
            if isinstance(relation, dict):
                result.append(dict(relation))
                continue
            if hasattr(relation, "__dict__"):
                result.append(cls._convert_relation_object_to_dict(relation))
                continue
            result.append({"ownership_id": relation})
        return result

    @staticmethod
    def _build_party_relations(
        ownership_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        party_relations: list[dict[str, Any]] = []
        for relation in ownership_relations:
            if not isinstance(relation, dict):
                continue
            ownership_id = relation.get("ownership_id")
            if ownership_id is None or str(ownership_id).strip() == "":
                continue

            is_primary_raw = relation.get("is_primary")
            is_primary = True if is_primary_raw is None else bool(is_primary_raw)
            is_active_raw = relation.get("is_active")
            is_active = True if is_active_raw is None else bool(is_active_raw)
            party_relations.append(
                {
                    "id": relation.get("id"),
                    "project_id": relation.get("project_id"),
                    "party_id": str(ownership_id),
                    "party_name": relation.get("ownership_name"),
                    "relation_type": "owner",
                    "is_primary": is_primary,
                    "is_active": is_active,
                }
            )
        return party_relations

    @model_validator(mode="before")
    @classmethod
    def coerce_project_model(cls, v: Any) -> Any:
        """避免在响应序列化中触发懒加载关系。"""
        if isinstance(v, dict):
            return v
        try:
            state = sa_inspect(v)
        except Exception:
            return v

        data = {attr.key: getattr(v, attr.key) for attr in state.mapper.column_attrs}

        try:
            rel_state = state.attrs.ownership_relations
            rel_value = rel_state.loaded_value
            no_value = getattr(orm_attributes, "NO_VALUE", None)
            data["party_relations"] = [] if rel_value is no_value else rel_value
        except Exception:
            data["party_relations"] = []

        if hasattr(v, "asset_count"):
            data["asset_count"] = getattr(v, "asset_count")

        if "created_by" not in data:
            data["created_by"] = getattr(v, "created_by", None)
        if "updated_by" not in data:
            data["updated_by"] = getattr(v, "updated_by", None)

        data.setdefault("party_relations", [])
        return data

    @field_validator("party_relations", mode="before")
    @classmethod
    def convert_party_relations(cls, v: Any) -> list[dict[str, Any]]:
        """转换主体关系对象并统一输出 party_relations。"""
        if v is None:
            return []

        if isinstance(v, list):
            if len(v) == 0:
                return []
            first_item = v[0]
            if isinstance(first_item, dict) and "party_id" in first_item:
                return [dict(item) if isinstance(item, dict) else item for item in v]

        ownership_relations = cls._serialize_ownership_relations(v)
        return cls._build_party_relations(ownership_relations)

    @model_validator(mode="after")
    def ensure_party_relations(self) -> "ProjectResponse":
        if self.party_relations is None:
            self.party_relations = []
        return self

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """项目列表响应模式"""

    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectAssetSummary(BaseModel):
    """项目有效资产面积汇总。"""

    total_assets: int
    total_rentable_area: float
    total_rented_area: float
    occupancy_rate: float


class ProjectActiveAssetsResponse(BaseModel):
    """项目有效关联资产列表响应。"""

    items: list["AssetListItemResponse"]
    total: int
    summary: ProjectAssetSummary


class ProjectDeleteResponse(BaseModel):
    """项目删除响应模式"""

    message: str
    deleted_id: str
    affected_assets: int


class ProjectSearchRequest(BaseModel):
    """项目搜索请求模式"""

    keyword: str | None = Field(None, description="搜索关键词")
    status: str | None = Field(None, description="业务状态")
    owner_party_id: str | None = Field(None, description="产权方主体ID")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页大小")


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应模式"""

    total_projects: int
    active_projects: int
