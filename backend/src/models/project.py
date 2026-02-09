"""项目模型。"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Boolean, Date, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .asset import Asset
    from .project_relations import ProjectOwnershipRelation


class Project(Base):
    """项目模型"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    short_name: Mapped[str | None] = mapped_column(String(100), comment="项目简称")
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="项目编码"
    )
    project_type: Mapped[str | None] = mapped_column(String(50), comment="项目类型")
    project_scale: Mapped[str | None] = mapped_column(String(50), comment="项目规模")
    project_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="规划中", comment="项目状态"
    )
    start_date: Mapped[date | None] = mapped_column(Date, comment="开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, comment="结束日期")
    expected_completion_date: Mapped[date | None] = mapped_column(
        Date, comment="预计完成日期"
    )
    actual_completion_date: Mapped[date | None] = mapped_column(
        Date, comment="实际完成日期"
    )

    address: Mapped[str | None] = mapped_column(String(500), comment="项目地址")
    city: Mapped[str | None] = mapped_column(String(100), comment="城市")
    district: Mapped[str | None] = mapped_column(String(100), comment="区域")
    province: Mapped[str | None] = mapped_column(String(100), comment="省份")

    project_manager: Mapped[str | None] = mapped_column(String(100), comment="项目经理")
    project_phone: Mapped[str | None] = mapped_column(String(50), comment="项目电话")
    project_email: Mapped[str | None] = mapped_column(String(100), comment="项目邮箱")

    total_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="总投资"
    )
    planned_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="计划投资"
    )
    actual_investment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="实际投资"
    )
    project_budget: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), comment="项目预算"
    )

    project_description: Mapped[str | None] = mapped_column(Text, comment="项目描述")
    project_objectives: Mapped[str | None] = mapped_column(Text, comment="项目目标")
    project_scope: Mapped[str | None] = mapped_column(Text, comment="项目范围")

    management_entity: Mapped[str | None] = mapped_column(
        String(200), comment="管理单位"
    )
    ownership_entity: Mapped[str | None] = mapped_column(
        String(200), comment="权属单位"
    )
    construction_company: Mapped[str | None] = mapped_column(
        String(200), comment="施工单位"
    )
    design_company: Mapped[str | None] = mapped_column(String(200), comment="设计单位")
    supervision_company: Mapped[str | None] = mapped_column(
        String(200), comment="监理单位"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否启用"
    )
    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan"
    )
    ownership_relations: Mapped[list["ProjectOwnershipRelation"]] = relationship(
        "ProjectOwnershipRelation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, code={self.code})>"


__all__ = ["Project"]
