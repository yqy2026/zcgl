"""
项目管理相关数据模式
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectBase(BaseModel):
    """项目基础模式"""

    name: str = Field(..., title="项目名称", min_length=1, max_length=200)
    short_name: str | None = Field(None, title="项目简称", max_length=100)
    code: str | None = Field(None, title="项目编码", min_length=1, max_length=100)
    project_type: str | None = Field(None, title="项目类型", max_length=50)
    project_scale: str | None = Field(None, title="项目规模", max_length=50)
    project_status: str | None = Field("规划中", title="项目状态", max_length=50)
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
    management_entity: str | None = Field(None, title="管理单位", max_length=200)
    ownership_entity: str | None = Field(None, title="权属单位", max_length=200)
    construction_company: str | None = Field(None, title="施工单位", max_length=200)
    design_company: str | None = Field(None, title="设计单位", max_length=200)
    supervision_company: str | None = Field(None, title="监理单位", max_length=200)
    is_active: bool | None = Field(True, title="是否启用")
    data_status: str | None = Field("正常", title="数据状态", max_length=20)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        """验证项目编码格式"""
        if v is not None:
            # 验证编码格式：[前缀][年月][序号]
            import re

            pattern = r"^[A-Z]{2}\d{7,8}$"  # 2字母前缀 + 7或8位数字 (兼容新旧格式)
            if not re.match(pattern, v):
                raise ValueError(
                    "项目编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: PJ2509001 或 PJ25091001"
                )
            return v.upper()
        return v


class ProjectCreate(ProjectBase):
    """创建项目模式"""

    ownership_relations: list[dict] | None = Field(None, title="权属方关系")
    ownership_ids: list[str] | None = Field(None, title="权属方ID列表")


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
    management_entity: str | None = Field(None, title="管理单位", max_length=200)
    ownership_entity: str | None = Field(None, title="权属单位", max_length=200)
    construction_company: str | None = Field(None, title="施工单位", max_length=200)
    design_company: str | None = Field(None, title="设计单位", max_length=200)
    supervision_company: str | None = Field(None, title="监理单位", max_length=200)
    is_active: bool | None = Field(None, title="是否启用")
    data_status: str | None = Field(None, title="数据状态", max_length=20)
    ownership_relations: list[dict] | None = Field(None, title="权属方关系")
    ownership_ids: list[str] | None = Field(None, title="权属方ID列表")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        """验证项目编码格式"""
        if v is not None:
            # 验证编码格式：[前缀][年月][序号]
            import re

            pattern = r"^[A-Z]{2}\d{7,8}$"  # 2字母前缀 + 7或8位数字 (兼容新旧格式)
            if not re.match(pattern, v):
                raise ValueError(
                    "项目编码格式必须为: [2字母前缀][4位年月][3位序号]，例如: PJ2509001 或 PJ25091001"
                )
            return v.upper()
        return v


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
    ownership_relations: list[dict] | None = None

    @field_validator("ownership_relations", mode="before")
    @classmethod
    def convert_ownership_relations(cls, v):
        """转换权属方关系对象为字典格式"""
        if v is None:
            return None

        # 如果是SQLAlchemy关系对象列表，转换为字典
        if hasattr(v, "__iter__") and not isinstance(v, dict):
            result = []
            for relation in v:
                if hasattr(relation, "__dict__"):
                    # SQLAlchemy对象转换为字典
                    relation_dict = {
                        "id": getattr(relation, "id", None),
                        "project_id": getattr(relation, "project_id", None),
                        "ownership_id": getattr(relation, "ownership_id", None),
                        "is_active": getattr(relation, "is_active", True),
                        "created_at": getattr(relation, "created_at", None),
                        "updated_at": getattr(relation, "updated_at", None),
                    }

                    # 尝试获取关联的权属方名称
                    if hasattr(relation, "ownership") and relation.ownership:
                        ownership = relation.ownership
                        relation_dict["ownership_name"] = getattr(
                            ownership, "name", None
                        )
                        relation_dict["ownership_code"] = getattr(
                            ownership, "code", None
                        )
                        relation_dict["ownership_short_name"] = getattr(
                            ownership, "short_name", None
                        )

                    result.append(relation_dict)
                else:
                    # 已经是字典格式，直接添加
                    result.append(relation)
            return result

        # 如果是字典格式，直接返回
        return v

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """项目列表响应模式"""

    items: list[ProjectResponse]
    total: int
    page: int
    size: int
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
    size: int = Field(10, ge=1, le=100, description="每页大小")


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应模式"""

    total_count: int
    active_count: int
    inactive_count: int
    type_distribution: dict | None = None
    status_distribution: dict | None = None
    city_distribution: dict | None = None
    investment_stats: dict | None = None
    recent_created: list | None = None
