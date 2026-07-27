"""Property certificate CRUD service without document extraction adapters."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BusinessValidationError
from ...crud.asset import asset_crud
from ...crud.property_certificate import property_certificate_crud
from ...crud.query_builder import PartyFilter
from ...models.property_certificate import CertificateType, PropertyCertificate
from ...schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
)
from ...services.party.service import party_service
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class PropertyCertificateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_certificates(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[PropertyCertificate]:
        resolved = await self._resolve_party_filter(
            current_user_id=current_user_id, party_filter=party_filter
        )
        if resolved is not None and not any(
            str(value).strip() for value in resolved.party_ids
        ):
            return []
        return await property_certificate_crud.get_multi(
            self.db, skip=skip, limit=limit, party_filter=resolved
        )

    async def get_certificate(
        self,
        certificate_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> PropertyCertificate | None:
        resolved = await self._resolve_party_filter(
            current_user_id=current_user_id, party_filter=party_filter
        )
        if resolved is not None and not any(
            str(value).strip() for value in resolved.party_ids
        ):
            return None
        return await property_certificate_crud.get(
            self.db, certificate_id, party_filter=resolved
        )

    async def create_certificate(
        self,
        certificate: PropertyCertificateCreate,
        *,
        created_by: str | None = None,
        organization_id: str | None = None,
    ) -> PropertyCertificate:
        asset_ids = self._normalize_ids(certificate.asset_ids)
        holder_party_ids = self._normalize_ids(certificate.holder_party_ids)
        await self._assert_write_gate(
            certificate, asset_ids, holder_party_ids, "property_certificate:create"
        )
        normalized = certificate.model_copy(
            update={
                "certificate_number": certificate.certificate_number.strip(),
                "asset_ids": asset_ids,
                "holder_party_ids": holder_party_ids,
            }
        )
        return await property_certificate_crud.create_with_owners_async(
            self.db,
            obj_in=normalized,
            owner_ids=holder_party_ids,
            asset_ids=asset_ids,
            created_by=created_by,
            organization_id=organization_id,
        )

    async def update_certificate(
        self, certificate: PropertyCertificate, update: PropertyCertificateUpdate
    ) -> PropertyCertificate:
        asset_ids = (
            self._normalize_ids(update.asset_ids)
            if "asset_ids" in update.model_fields_set
            else None
        )
        holder_party_ids = (
            self._normalize_ids(update.holder_party_ids)
            if "holder_party_ids" in update.model_fields_set
            else None
        )
        if asset_ids is not None and not asset_ids:
            raise BusinessValidationError(
                "linked assets are required",
                field_errors={"asset_ids": ["at least one linked asset is required"]},
            )
        if holder_party_ids is not None:
            if not holder_party_ids:
                raise BusinessValidationError(
                    "holder parties are required",
                    field_errors={
                        "holder_party_ids": [
                            "at least one approved holder party is required"
                        ]
                    },
                )
            await party_service.assert_parties_approved(
                self.db,
                party_ids=holder_party_ids,
                operation="property_certificate:update",
            )
        if asset_ids is not None:
            await self._assert_assets_exist(asset_ids)
        return await property_certificate_crud.update_with_relations_async(
            self.db,
            db_obj=certificate,
            obj_in=update,
            owner_ids=holder_party_ids,
            asset_ids=asset_ids,
        )

    async def delete_certificate(self, certificate_id: str) -> None:
        await property_certificate_crud.remove(self.db, id=certificate_id)

    async def _resolve_party_filter(
        self, *, current_user_id: str | None, party_filter: PartyFilter | None
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            self.db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    async def _assert_write_gate(
        self,
        certificate: PropertyCertificateCreate,
        asset_ids: list[str],
        holder_party_ids: list[str],
        operation: str,
    ) -> None:
        errors: dict[str, list[str]] = {}
        number = certificate.certificate_number.strip()
        if not number:
            errors["certificate_number"] = ["certificate_number is required"]
        elif await property_certificate_crud.get_by_certificate_number_async(
            self.db, number
        ):
            errors["certificate_number"] = [
                "certificate_number must be globally unique"
            ]
        if (
            self._requires_property_address(certificate.certificate_type)
            and not (certificate.property_address or "").strip()
        ):
            errors["property_address"] = [
                "property_address is required for property certificate types"
            ]
        if not asset_ids:
            errors["asset_ids"] = ["at least one linked asset is required"]
        if not holder_party_ids:
            errors["holder_party_ids"] = [
                "at least one approved holder party is required"
            ]
        if errors:
            raise BusinessValidationError(
                "property certificate save gate failed", field_errors=errors
            )
        await self._assert_assets_exist(asset_ids)
        await party_service.assert_parties_approved(
            self.db, party_ids=holder_party_ids, operation=operation
        )

    async def _assert_assets_exist(self, asset_ids: list[str]) -> None:
        found = {
            str(asset.id)
            for asset in await asset_crud.get_multi_by_ids_async(
                self.db, ids=asset_ids, include_deleted=False
            )
        }
        missing = [asset_id for asset_id in asset_ids if asset_id not in found]
        if missing:
            raise BusinessValidationError(
                "linked assets must exist",
                field_errors={"asset_ids": [", ".join(missing)]},
            )

    @staticmethod
    def _normalize_ids(values: list[str] | None) -> list[str]:
        result: list[str] = []
        for value in values or []:
            normalized = str(value).strip()
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    @staticmethod
    def _requires_property_address(certificate_type: str) -> bool:
        try:
            return CertificateType(certificate_type) in {
                CertificateType.REAL_ESTATE,
                CertificateType.HOUSE_OWNERSHIP,
                CertificateType.LAND_USE,
            }
        except ValueError:
            return True
