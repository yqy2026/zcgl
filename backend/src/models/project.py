"""项目模型。"""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .asset import Asset
    from .party import Party


class ProjectStatus(str, enum.Enum):
    """项目业务状态（英文代码值）。"""

    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class ProjectReviewStatus(str, enum.Enum):
    """项目审核状态（英文代码值）。"""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Project(Base):
    """项目模型（运营管理归集单元）。"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    project_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="项目名称"
    )
    project_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="项目编码（PRJ-<SEGMENT>-<SERIAL>）",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ProjectStatus.PLANNING.value,
        comment="业务状态：planning/active/paused/completed/terminated",
    )

    manager_party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        index=True,
        comment="项目运营管理主体ID",
    )

    # 审核字段
    review_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ProjectReviewStatus.DRAFT.value,
        comment="审核状态：draft/pending/approved/rejected",
    )
    review_by: Mapped[str | None] = mapped_column(String(100), comment="审核人")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    review_reason: Mapped[str | None] = mapped_column(
        Text, comment="审核原因（反审核时必填）"
    )

    data_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="正常", comment="数据状态：正常/已删除"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="创建时间",
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

    # 使用 project_assets 间接关联资产
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary="project_assets",
        primaryjoin="Project.id == ProjectAsset.project_id",
        secondaryjoin="Asset.id == ProjectAsset.asset_id",
        viewonly=True,
    )
    manager_party: Mapped["Party | None"] = relationship(
        "Party",
        foreign_keys=[manager_party_id],
    )

    def __init__(self, **kwargs: object) -> None:
        # 丢弃已废弃的旧字段键，防止构造时报错
        for _legacy in (
            "management_entity",
            "ownership_entity",
            "organization_id",
            "name",
            "code",
            "project_status",
            "is_active",
            "short_name",
            "project_type",
            "project_scale",
            "start_date",
            "end_date",
            "expected_completion_date",
            "actual_completion_date",
            "address",
            "city",
            "district",
            "province",
            "project_manager",
            "project_phone",
            "project_email",
            "total_investment",
            "planned_investment",
            "actual_investment",
            "project_budget",
            "project_description",
            "project_objectives",
            "project_scope",
            "construction_company",
            "design_company",
            "supervision_company",
        ):
            kwargs.pop(_legacy, None)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, project_name={self.project_name}, project_code={self.project_code})>"


__all__ = ["Project", "ProjectStatus", "ProjectReviewStatus"]
