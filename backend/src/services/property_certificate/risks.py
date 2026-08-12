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


def _normalized_enum_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value or "").strip().lower()


def _is_current_holder_relation(
    relation: HolderRelationSnapshot, *, as_of: datetime
) -> bool:
    return (
        _normalized_enum_value(relation.relation_role) in _CURRENT_HOLDER_ROLES
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
    "IncompleteCertificateInfoResult",
    "HolderRelationSnapshot",
    "PropertyCertificateDataQualityWarning",
    "calculate_holder_owner_mismatch",
    "calculate_incomplete_certificate_info",
]


_INCOMPLETE_CERTIFICATE_INFO = "incomplete_certificate_info"
# 按证照类型条件化的「证载信息」字段集（domain-model §4.20：缺失只 warning）。
# 未知类型保守处理为仅检查全类型适用的 restrictions，避免类型不相关误报。
_INCOMPLETE_FIELD_SETS: dict[str, tuple[str, ...]] = {
    "real_estate": (
        "building_area",
        "land_area",
        "land_use_term_start",
        "land_use_term_end",
        "restrictions",
    ),
    "house_ownership": ("building_area", "restrictions"),
    "land_use": (
        "land_area",
        "land_use_term_start",
        "land_use_term_end",
        "restrictions",
    ),
    "other": ("restrictions",),
}
_INCOMPLETE_FIELD_LABELS: dict[str, str] = {
    "building_area": "证载建筑面积",
    "land_area": "证载土地面积",
    "land_use_term_start": "土地使用期限起",
    "land_use_term_end": "土地使用期限止",
    "restrictions": "限制信息",
}


@dataclass(frozen=True, slots=True)
class IncompleteCertificateInfoResult:
    missing_field_keys: tuple[str, ...]
    warnings: tuple[PropertyCertificateDataQualityWarning, ...]





def _field_is_missing(value: object | None) -> bool:
    return value is None or str(value).strip() == ""


def calculate_incomplete_certificate_info(
    *,
    certificate_id: str,
    certificate_number: str,
    certificate_type: object,
    building_area: object | None = None,
    land_area: object | None = None,
    land_use_term_start: object | None = None,
    land_use_term_end: object | None = None,
    restrictions: object | None = None,
    assets: Iterable[AssetOwnerSnapshot] = (),
) -> IncompleteCertificateInfoResult:
    """Derive one 证照信息不完整 warning for each certificate/asset pair."""
    normalized_certificate_id = _normalized_id(certificate_id)
    field_values = {
        "building_area": building_area,
        "land_area": land_area,
        "land_use_term_start": land_use_term_start,
        "land_use_term_end": land_use_term_end,
        "restrictions": restrictions,
    }
    checked_fields = _INCOMPLETE_FIELD_SETS.get(
        _normalized_enum_value(certificate_type),
        _INCOMPLETE_FIELD_SETS["other"],
    )
    missing_field_keys = tuple(
        field_key
        for field_key in checked_fields
        if _field_is_missing(field_values[field_key])
    )
    if not missing_field_keys:
        return IncompleteCertificateInfoResult(
            missing_field_keys=(), warnings=()
        )

    missing_labels = "、".join(
        _INCOMPLETE_FIELD_LABELS[field_key] for field_key in missing_field_keys
    )
    certificate_label = (
        _normalized_id(certificate_number) or normalized_certificate_id
    )
    warnings: list[PropertyCertificateDataQualityWarning] = []
    for asset in sorted(assets, key=lambda item: _normalized_id(item.asset_id)):
        asset_id = _normalized_id(asset.asset_id)
        if asset_id == "":
            continue
        asset_label = _normalized_id(asset.asset_name) or asset_id
        warnings.append(
            PropertyCertificateDataQualityWarning(
                risk_id=(
                    f"property-certificate:{normalized_certificate_id}:"
                    f"asset:{asset_id}:{_INCOMPLETE_CERTIFICATE_INFO}"
                ),
                risk_type=_INCOMPLETE_CERTIFICATE_INFO,
                severity="warning",
                message=(
                    f"产权证 {certificate_label} 证照信息不完整：缺失 {missing_labels}"
                    f"（资产 {asset_label}）"
                ),
                certificate_id=normalized_certificate_id,
                asset_id=asset_id,
            )
        )
    return IncompleteCertificateInfoResult(
        missing_field_keys=missing_field_keys,
        warnings=tuple(warnings),
    )
