"""
Asset search blind index table.
Stores HMAC hashes of n-gram tokens for encrypted fields.
"""

from sqlalchemy import Column, ForeignKey, Integer, String

from ..database import Base


class AssetSearchIndex(Base):
    __tablename__ = "asset_search_index"

    asset_id = Column(
        String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    field_name = Column(String(50), primary_key=True)
    token_hash = Column(String(64), primary_key=True)
    key_version = Column(Integer, primary_key=True)

    def __repr__(self) -> str:
        return (
            "<AssetSearchIndex("
            f"asset_id={self.asset_id}, field={self.field_name}, "
            f"key_version={self.key_version})>"
        )
