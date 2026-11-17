"""Sync xlsx export for the property (asset-unit) ledger table.

The exported sheet mirrors the columns the 物业 page renders (prototype
asset-ops-v5: 资产单元/业态/产权方/建筑面积/可租面积/性质/考核/出租状态/
租户·至/产权证), one row per unit, capped at a page-independent maximum.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from ...schemas.asset_operations import AssetUnitDetail
from .ledger_export_service import XLSX_MEDIA_TYPE

EXPORT_ROW_LIMIT = 5000

_STATUS_LABELS = {
    "rented": "已出租",
    "vacant": "空置可租",
    "non_rentable": "不可租",
}
_ASSESSMENT_LABELS = {
    "included": "纳入",
    "excluded": "不纳入",
    "pending": "待确认",
}
_VACANCY_REASON_LABELS = {
    "renovation": "装修中",
    "marketing": "招商中",
    "repossession": "待收回",
    "pending_contract": "有意向未签",
    "other": "其他",
}


def _workbook_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_asset_unit_workbook(
    items: list[AssetUnitDetail], *, year: int
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "物业台账"
    sheet.append(
        [
            "单元编号",
            "名称",
            "项目",
            "业态",
            "产权方",
            "建筑面积(㎡)",
            "可租面积(㎡)",
            "性质",
            f"{year} 考核",
            "出租状态",
            "当前租户",
            "租期至",
            "产权证数",
        ]
    )
    for item in items:
        nature = "经营性" if item.is_operating else "非经营"
        status = _STATUS_LABELS.get(item.rental_status, item.rental_status)
        if item.rental_status == "vacant" and item.vacancy_reason is not None:
            reason = _VACANCY_REASON_LABELS.get(
                item.vacancy_reason, item.vacancy_reason
            )
            status = f"空置可租 · {reason}"
        sheet.append(
            [
                item.unit_code,
                item.name,
                item.project_name,
                item.usage_type or "",
                item.owner_party_name,
                item.building_area,
                item.rentable_area,
                nature,
                _ASSESSMENT_LABELS.get(item.assessment, "—"),
                status,
                item.current_tenant_name or "",
                item.current_contract_end_date or "",
                item.certificate_count,
            ]
        )
    return _workbook_bytes(workbook)


__all__ = [
    "EXPORT_ROW_LIMIT",
    "XLSX_MEDIA_TYPE",
    "build_asset_unit_workbook",
]
