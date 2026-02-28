"""
项目管理相关数据模式
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import attributes as orm_attributes


class ProjectBase(BaseModel):
    """项目基础模式"""

    name: str = Field(..., title="项目名称", min_length=1, max_length=200)
    short_name: str | None = Field(None, title="项目简称", max_length=100)
    code: str | None = Field(None, title="项目编码", min_length=1, max_length=100)
    project_type: str | None = Field(None, title="项目类型", max_length=50)
    project_scale: str | None = Field(None, title="项目规模", max_length=50)
    project_status: str = Field("规划中", title="项目状态", max_length=50)
    start_date: str | None = Field(None, title="开始日期")
    end_date: str | None = Field(None, title="结束日期")
    expected_completion_date: str | None = Field(None, title="预计完成日期")
    actual_completion_date: str | None = Field(None, title="实际完成日期")
    address: str | None = Field(None, title="项目地址", max_length=500)
    city: str | None = Field(None, title="城市", max_length=100)
    district: str | None = Field(None, title="区域", max_length=100)
    province: str | None = Field(None, title="省份", max_length=100)
    project_manager: str | None = Field(None, title="项目经理", max_length=100)
    project_phone: str | None = Field(None, title="项目电话", max_length=50)
    project_email: str | None = Field(None, title="项目邮箱", max_length=100)
    total_investment: float | None = Field(None, title="总投资")
    planned_investment: float | None = Field(None, title="计划投资")
    actual_investment: float | None = Field(None, title="实际投资")
    project_budget: float | None = Field(None, title="项目预算")
    project_description: str | None = Field(None, title="项目描述")
    project_objectives: str | None = Field(None, title="项目目标")
    project_scope: str | None = Field(None, title="项目范围")
    management_entity: str | None = Field(
        None, title="管理单位（DEPRECATED）", max_length=200
    )
    organization_id: str | None = Field(None, title="所属组织ID（DEPRECATED）")
    manager_party_id: str | None = Field(None, title="经营管理主体ID")
    ownership_entity: str | None = Field(
        None, title="权属单位（DEPRECATED）", max_length=200
    )
    construction_company: str | None = Field(None, title="施工单位", max_length=200)
    design_company: str | None = Field(None, title="设计单位", max_length=200)
    supervision_company: str | None = Field(None, title="监理单位", max_length=200)
    is_active: bool = Field(True, title="是否启用")
    data_status: str = Field("正常", title="数据状态", max_length=20)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str | None) -> str | None:
        """验证项目编码格式"""
        if v is not None:  # pragma: no cover
            # 验证编码格式：[前缀][年月][序号]
            import re  # pragma: no cover

            pattern = r"^[A-Z]{2}\d{7,8}$"  # pragma: no cover
            if not re.match(pattern, v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_project_code",
                    "项目编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: PJ2509001 或 PJ25091001",
                    {},
                )  # pragma: no cover
            return v.upper()  # pragma: no cover
        return v  # pragma: no cover


class ProjectCreate(ProjectBase):
    """创建项目模式"""

    ownership_relations: list[dict[str, Any]] | None = Field(None, title="权属方关系")
    ownership_ids: list[str] | None = Field(None, title="权属方ID列表（DEPRECATED）")


class ProjectUpdate(BaseModel):
    """更新项目模式"""

    name: str | None = Field(None, title="项目名称", min_length=1, max_length=200)
    short_name: str | None = Field(None, title="项目简称", max_length=100)
    code: str | None = Field(None, title="项目编码", min_length=1, max_length=100)
    project_type: str | None = Field(None, title="项目类型", max_length=50)
    project_scale: str | None = Field(None, title="项目规模", max_length=50)
    project_status: str | None = Field(None, title="项目状态", max_length=50)
    start_date: str | None = Field(None, title="开始日期")
    end_date: str | None = Field(None, title="结束日期")
    expected_completion_date: str | None = Field(None, title="预计完成日期")
    actual_completion_date: str | None = Field(None, title="实际完成日期")
    address: str | None = Field(None, title="项目地址", max_length=500)
    city: str | None = Field(None, title="城市", max_length=100)
    district: str | None = Field(None, title="区域", max_length=100)
    province: str | None = Field(None, title="省份", max_length=100)
    project_manager: str | None = Field(None, title="项目经理", max_length=100)
    project_phone: str | None = Field(None, title="项目电话", max_length=50)
    project_email: str | None = Field(None, title="项目邮箱", max_length=100)
    total_investment: float | None = Field(None, title="总投资")
    planned_investment: float | None = Field(None, title="计划投资")
    actual_investment: float | None = Field(None, title="实际投资")
    project_budget: float | None = Field(None, title="项目预算")
    project_description: str | None = Field(None, title="项目描述")
    project_objectives: str | None = Field(None, title="项目目标")
    project_scope: str | None = Field(None, title="项目范围")
    management_entity: str | None = Field(
        None, title="管理单位（DEPRECATED）", max_length=200
    )
    organization_id: str | None = Field(None, title="所属组织ID（DEPRECATED）")
    manager_party_id: str | None = Field(None, title="经营管理主体ID")
    ownership_entity: str | None = Field(
        None, title="权属单位（DEPRECATED）", max_length=200
    )
    construction_company: str | None = Field(None, title="施工单位", max_length=200)
    design_company: str | None = Field(None, title="设计单位", max_length=200)
    supervision_company: str | None = Field(None, title="监理单位", max_length=200)
    is_active: bool | None = Field(None, title="是否启用")
    data_status: str | None = Field(None, title="数据状态", max_length=20)
    ownership_relations: list[dict[str, Any]] | None = Field(None, title="权属方关系")
    ownership_ids: list[str] | None = Field(None, title="权属方ID列表（DEPRECATED）")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str | None) -> str | None:
        """验证项目编码格式"""
        if v is not None:  # pragma: no cover
            # 验证编码格式：[前缀][年月][序号]
            import re  # pragma: no cover

            pattern = r"^[A-Z]{2}\d{7,8}$"  # pragma: no cover
            if not re.match(pattern, v):  # pragma: no cover
                raise PydanticCustomError(  # pragma: no cover
                    "invalid_project_code",
                    "项目编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: PJ2509001 或 PJ25091001",
                    {},
                )  # pragma: no cover
            return v.upper()  # pragma: no cover
        return v  # pragma: no cover


class ProjectResponse(ProjectBase):
    """项目响应模式"""

    id: str
    is_active: bool
    data_status: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None
    asset_count: int = 0
    ownership_relations: list[dict[str, Any]] | None = None
    party_relations: list[dict[str, Any]] = Field(
        default_factory=list, title="主体关系（兼容 ownership_relations 转换）"
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
            relation_dict["ownership_name"] = getattr(ownership, "name", None)
            relation_dict["ownership_code"] = getattr(ownership, "code", None)
            relation_dict["ownership_short_name"] = getattr(ownership, "short_name", None)
        return relation_dict

    @classmethod
    def _serialize_ownership_relations(cls, v: Any) -> list[dict[str, Any]] | Any:
        if v is None:
            return None
        if not hasattr(v, "__iter__") or isinstance(v, dict):
            return v

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
        ownership_relations: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        if ownership_relations is None:
            return []

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
            data["ownership_relations"] = None if rel_value is no_value else rel_value
        except Exception:
            data["ownership_relations"] = None

        if hasattr(v, "asset_count"):
            data["asset_count"] = getattr(v, "asset_count")

        if "created_by" not in data:
            data["created_by"] = getattr(v, "created_by", None)
        if "updated_by" not in data:
            data["updated_by"] = getattr(v, "updated_by", None)

        data.setdefault("party_relations", data.get("ownership_relations"))
        return data

    @field_validator("ownership_relations", mode="before")
    @classmethod
    def convert_ownership_relations(cls, v: Any) -> Any:
        """转换权属方关系对象为字典格式"""
        return cls._serialize_ownership_relations(v)

    @field_validator("party_relations", mode="before")
    @classmethod
    def convert_party_relations(cls, v: Any) -> list[dict[str, Any]]:
        """兼容 ownership_relations 输入并统一输出 party_relations。"""
        if v is None:
            return []

        if isinstance(v, list):
            if len(v) == 0:
                return []
            first_item = v[0]
            if isinstance(first_item, dict) and "party_id" in first_item:
                return [dict(item) if isinstance(item, dict) else item for item in v]

        ownership_relations = cls._serialize_ownership_relations(v)
        if isinstance(ownership_relations, list):
            return cls._build_party_relations(ownership_relations)
        return []

    @model_validator(mode="after")
    def ensure_party_relations(self) -> "ProjectResponse":
        if len(self.party_relations) > 0:
            return self
        self.party_relations = self._build_party_relations(self.ownership_relations)
        return self

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """项目列表响应模式"""

    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectDeleteResponse(BaseModel):
    """项目删除响应模式"""

    message: str
    deleted_id: str
    affected_assets: int


class ProjectSearchRequest(BaseModel):
    """项目搜索请求模式"""

    keyword: str | None = Field(None, description="搜索关键词")
    is_active: bool | None = Field(None, description="是否启用")
    project_type: str | None = Field(None, description="项目类型")
    project_status: str | None = Field(None, description="项目状态")
    city: str | None = Field(None, description="城市")
    ownership_id: str | None = Field(None, description="权属方ID")
    ownership_entity: str | None = Field(None, description="权属方名称")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页大小")


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应模式"""

    total_count: int
    active_count: int
    inactive_count: int
    type_distribution: dict[str, int] | None = None
    status_distribution: dict[str, int] | None = None
    city_distribution: dict[str, int] | None = None
    investment_stats: dict[str, float] | None = None
    recent_created: list[dict[str, Any]] | None = None
