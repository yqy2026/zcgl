"""资产历史与文档模型。"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .asset import Asset


class AssetHistory(Base):
    """资产变更历史模型"""

    __tablename__ = "asset_history"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_id: Mapped[str] = mapped_column(
        String, ForeignKey("assets.id"), index=True, nullable=False, comment="资产ID"
    )
    operation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="操作类型"
    )
    field_name: Mapped[str | None] = mapped_column(String(100), comment="字段名称")
    old_value: Mapped[str | None] = mapped_column(Text, comment="原值")
    new_value: Mapped[str | None] = mapped_column(Text, comment="新值")
    operator: Mapped[str | None] = mapped_column(String(100), comment="操作人")
    operation_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="操作时间",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="操作描述")

    change_reason: Mapped[str | None] = mapped_column(String(200), comment="变更原因")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")
    session_id: Mapped[str | None] = mapped_column(String(100), comment="会话ID")

    asset: Mapped["Asset"] = relationship("Asset", back_populates="history_records")

    def __repr__(self) -> str:
        return f"<AssetHistory(id={self.id}, asset_id={self.asset_id}, operation={self.operation_type})>"


class AssetDocument(Base):
    """资产文档模型"""

    __tablename__ = "asset_documents"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_id: Mapped[str] = mapped_column(
        String, ForeignKey("assets.id"), index=True, nullable=False, comment="资产ID"
    )
    document_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="文档名称"
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="文档类型"
    )
    file_path: Mapped[str | None] = mapped_column(String(500), comment="文件路径")
    file_size: Mapped[int | None] = mapped_column(Integer, comment="文件大小(字节)")
    mime_type: Mapped[str | None] = mapped_column(String(100), comment="文件MIME类型")
    upload_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="上传时间",
    )
    uploader: Mapped[str | None] = mapped_column(String(100), comment="上传人")
    description: Mapped[str | None] = mapped_column(Text, comment="文档描述")

    asset: Mapped["Asset"] = relationship("Asset", back_populates="documents")

    def __repr__(self) -> str:
        return f"<AssetDocument(id={self.id}, name={self.document_name})>"


__all__ = ["AssetHistory", "AssetDocument"]
