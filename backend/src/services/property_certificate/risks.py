"""Pure property-certificate data-quality risk calculation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

_CURRENT_HOLDER_ROLES = frozenset({"owner", "co_owner"})
_HOLDER_OWNER_MISMATCH = "holder_owner_mismatch"


@dataclass(frozen=True, slots=True)
class HolderRelationSnapshot:
    party_id: str
    relation_role: str
    valid_from: datetime
    valid_to: datetime | None


@dataclass(frozen=True, slots=True)
class AssetOwnerSnapshot:
    asset_id: str
    owner_party_id: str | None
    asset_name: str | None = None


@dataclass(frozen=True, slots=True)
class PropertyCertificateDataQualityWarning:
    risk_id: str
    risk_type: str
    severity: str
    message: str
    certificate_id: str
    asset_id: str


@dataclass(frozen=True, slots=True)
class HolderOwnerMismatchResult:
    current_holder_party_ids: tuple[str, ...]
    warnings: tuple[PropertyCertificateDataQualityWarning, ...]
    missing_current_holders: bool
    asset_ids_missing_owner: tuple[str, ...]


def _normalized_id(value: object) -> str:
    return str(value or "").strip()


def _normalized_role(value: object) -> str:
    role_value = getattr(value, "value", value)
    return str(role_value or "").strip().lower()


def _is_current_holder_relation(
    relation: HolderRelationSnapshot, *, as_of: datetime
) -> bool:
    return (
        _normalized_role(relation.relation_role) in _CURRENT_HOLDER_ROLES
        and relation.valid_from <= as_of
        and (relation.valid_to is None or as_of < relation.valid_to)
    )


def calculate_holder_owner_mismatch(
    *,
    certificate_id: str,
    certificate_number: str,
    holder_relations: Iterable[HolderRelationSnapshot],
    assets: Iterable[AssetOwnerSnapshot],
    as_of: datetime,
) -> HolderOwnerMismatchResult:
    """Derive one mismatch warning for each certificate/asset pair."""
    normalized_certificate_id = _normalized_id(certificate_id)
    holder_party_ids = tuple(
        sorted(
            {
                party_id
                for relation in holder_relations
                if _is_current_holder_relation(relation, as_of=as_of)
                and (party_id := _normalized_id(relation.party_id)) != ""
            }
        )
    )
    holder_party_id_set = set(holder_party_ids)
    warnings: list[PropertyCertificateDataQualityWarning] = []
    asset_ids_missing_owner: list[str] = []

    for asset in sorted(assets, key=lambda item: _normalized_id(item.asset_id)):
        asset_id = _normalized_id(asset.asset_id)
        if asset_id == "":
            continue
        owner_party_id = _normalized_id(asset.owner_party_id)
        if owner_party_id == "":
            asset_ids_missing_owner.append(asset_id)
            continue
        if not holder_party_ids or owner_party_id in holder_party_id_set:
            continue

        certificate_label = (
            _normalized_id(certificate_number) or normalized_certificate_id
        )
        asset_label = _normalized_id(asset.asset_name) or asset_id
        warnings.append(
            PropertyCertificateDataQualityWarning(
                risk_id=(
                    f"property-certificate:{normalized_certificate_id}:"
                    f"asset:{asset_id}:{_HOLDER_OWNER_MISMATCH}"
                ),
                risk_type=_HOLDER_OWNER_MISMATCH,
                severity="warning",
                message=(
                    f"产权证 {certificate_label} 的当前权利人与资产 "
                    f"{asset_label} 的主产权主体不一致"
                ),
                certificate_id=normalized_certificate_id,
                asset_id=asset_id,
            )
        )

    return HolderOwnerMismatchResult(
        current_holder_party_ids=holder_party_ids,
        warnings=tuple(warnings),
        missing_current_holders=len(holder_party_ids) == 0,
        asset_ids_missing_owner=tuple(asset_ids_missing_owner),
    )


__all__ = [
    "AssetOwnerSnapshot",
    "HolderOwnerMismatchResult",
    "HolderRelationSnapshot",
    "PropertyCertificateDataQualityWarning",
    "calculate_holder_owner_mismatch",
]
