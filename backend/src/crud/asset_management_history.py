"""CRUD helpers for asset management-party history."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.asset_management_history import AssetManagementHistory


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDAssetManagementHistory:
    """AssetManagementHistory CRUD methods."""

    async def create(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        manager_party_id: str,
        start_date: date | None = None,
        change_reason: str | None = None,
        changed_by: str | None = None,
        agreement: str | None = None,
        commit: bool = True,
    ) -> AssetManagementHistory:
        record = AssetManagementHistory()
        record.asset_id = asset_id
        record.manager_party_id = manager_party_id
        record.start_date = start_date or date.today()
        record.change_reason = change_reason
        record.changed_by = changed_by
        record.agreement = agreement
        db.add(record)
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(record)
        return record

    async def close_active(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        manager_party_id: str,
        end_date: date | None = None,
        commit: bool = False,
    ) -> AssetManagementHistory | None:
        """Close the current active record for a given asset + manager."""
        stmt = (
            select(AssetManagementHistory)
            .where(
                AssetManagementHistory.asset_id == asset_id,
                AssetManagementHistory.manager_party_id == manager_party_id,
                AssetManagementHistory.end_date.is_(None),
            )
            .order_by(AssetManagementHistory.start_date.desc())
            .limit(1)
        )
        record = (await db.execute(stmt)).scalars().first()
        if record is None:
            return None
        record.end_date = end_date or date.today()
        record.updated_at = _utcnow_naive()
        if commit:
            await db.commit()
        else:
            await db.flush()
        await db.refresh(record)
        return record

    async def get_by_asset_id(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
    ) -> list[AssetManagementHistory]:
        stmt = (
            select(AssetManagementHistory)
            .where(AssetManagementHistory.asset_id == asset_id)
            .order_by(AssetManagementHistory.start_date.desc())
        )
        return list((await db.execute(stmt)).scalars().all())


asset_management_history_crud = CRUDAssetManagementHistory()

__all__ = ["CRUDAssetManagementHistory", "asset_management_history_crud"]
