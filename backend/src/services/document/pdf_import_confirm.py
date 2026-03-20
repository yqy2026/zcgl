"""
PDF 导入确认逻辑

从 pdf_import_service.py 拆分而来：用户确认导入数据后创建合同组/合同/租金条款。
"""

import logging
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import BaseBusinessError
from ...crud.pdf_import_session import pdf_import_session_crud
from ...models.contract_group import ContractDirection, GroupRelationType, RevenueMode
from ...models.pdf_import_session import ProcessingStep, SessionStatus
from ...schemas.contract_group import (
    AgencyDetailCreate,
    ContractCreate,
    ContractGroupCreate,
    ContractRentTermCreate,
    LeaseDetailCreate,
    SettlementRuleSchema,
)
from ...services.contract.contract_group_service import contract_group_service
from ...services.party import party_service
from ...utils.time import utcnow_naive
from .pdf_import_pipeline import _parse_date

logger = logging.getLogger(__name__)


# ── 辅助函数 ─────────────────────────────────────────────────────────────────


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized != "" else None


def _merge_confirmed_payload(confirmed_data: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    contract_data = confirmed_data.get("contract_data")
    if isinstance(contract_data, dict):
        merged.update(contract_data)
    for key, value in confirmed_data.items():
        if key != "contract_data":
            merged[key] = value
    return merged


def _parse_enum_member(enum_cls: Any, raw: Any) -> Any | None:
    if raw is None:
        return None
    if isinstance(raw, enum_cls):
        return raw
    normalized = _normalize_text(raw)
    if normalized is None:
        return None
    for member in enum_cls:
        if normalized == member.value or normalized.upper() == member.name:
            return member
    return None


def _parse_decimal(raw: Any, default: Decimal | None = None) -> Decimal | None:
    if raw is None:
        return default
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int | float):
        return Decimal(str(raw))
    normalized = _normalize_text(raw)
    if normalized is None:
        return default
    try:
        return Decimal(normalized)
    except (Decimal.InvalidOperation, ValueError):  # type: ignore[attr-defined]
        return None


# ── 确认导入主逻辑 ────────────────────────────────────────────────────────────


async def execute_confirm_import(
    db: AsyncSession,
    session_id: str,
    confirmed_data: dict[str, Any],
    user_id: str | int,
) -> dict[str, Any]:
    """用户验证数据后创建实际的资产/合同记录。"""
    import_session = await pdf_import_session_crud.get_by_session_id_async(
        db,
        session_id,
    )

    if not import_session:
        return {
            "success": False,
            "message": "Import session not found",
            "error": "Import session not found",
        }

    if import_session.status != SessionStatus.READY_FOR_REVIEW:
        return {
            "success": False,
            "message": "Import session is not ready for confirmation",
            "error": "Import session is not ready for confirmation",
        }

    merged_data = _merge_confirmed_payload(confirmed_data)
    required_fields = [
        "contract_number",
        "tenant_name",
        "start_date",
        "end_date",
        "revenue_mode",
        "operator_party_id",
        "owner_party_id",
        "contract_direction",
        "group_relation_type",
        "lessor_party_id",
        "lessee_party_id",
        "settlement_rule",
    ]
    missing_fields = [
        field for field in required_fields if merged_data.get(field) in (None, "")
    ]
    if missing_fields:
        msg = f"Missing required fields: {', '.join(missing_fields)}"
        return {"success": False, "message": msg, "error": msg}

    revenue_mode = _parse_enum_member(RevenueMode, merged_data.get("revenue_mode"))
    contract_direction = _parse_enum_member(
        ContractDirection, merged_data.get("contract_direction")
    )
    group_relation_type = _parse_enum_member(
        GroupRelationType, merged_data.get("group_relation_type")
    )
    if (
        revenue_mode is None
        or contract_direction is None
        or group_relation_type is None
    ):
        return {
            "success": False,
            "message": "Invalid enum values in confirmed_data",
            "error": "Invalid enum values in confirmed_data",
        }

    effective_from = _parse_date(merged_data.get("start_date"))
    effective_to = _parse_date(merged_data.get("end_date"))
    sign_date = _parse_date(merged_data.get("sign_date"))
    if effective_from is None or effective_to is None:
        return {
            "success": False,
            "message": "Invalid start_date or end_date format",
            "error": "Invalid start_date or end_date format",
        }
    if merged_data.get("sign_date") is not None and sign_date is None:
        return {
            "success": False,
            "message": "Invalid sign_date format",
            "error": "Invalid sign_date format",
        }

    monthly_rent_base = _parse_decimal(merged_data.get("monthly_rent_base"))
    if monthly_rent_base is None:
        return {
            "success": False,
            "message": "monthly_rent_base is required and must be a valid decimal",
            "error": "monthly_rent_base is required and must be a valid decimal",
        }

    asset_ids: list[str] = []
    if isinstance(merged_data.get("asset_ids"), list):
        asset_ids.extend(
            asset_id
            for raw_asset_id in merged_data.get("asset_ids", [])
            if (asset_id := _normalize_text(raw_asset_id)) is not None
        )
    single_asset_id = _normalize_text(merged_data.get("asset_id"))
    if single_asset_id is not None and single_asset_id not in asset_ids:
        asset_ids.append(single_asset_id)

    operator_party_id = _normalize_text(merged_data.get("operator_party_id"))
    owner_party_id = _normalize_text(merged_data.get("owner_party_id"))
    lessor_party_id = _normalize_text(merged_data.get("lessor_party_id"))
    lessee_party_id = _normalize_text(merged_data.get("lessee_party_id"))
    contract_number = _normalize_text(merged_data.get("contract_number"))
    if (
        operator_party_id is None
        or owner_party_id is None
        or lessor_party_id is None
        or lessee_party_id is None
        or contract_number is None
    ):
        return {
            "success": False,
            "message": "Missing required party ids or contract number",
            "error": "Missing required party ids or contract number",
        }

    settlement_rule_data = merged_data.get("settlement_rule")
    if not isinstance(settlement_rule_data, dict):
        return {
            "success": False,
            "message": "settlement_rule must be a JSON object",
            "error": "settlement_rule must be a JSON object",
        }

    total_deposit = _parse_decimal(merged_data.get("total_deposit"), Decimal("0"))
    if total_deposit is None:
        return {
            "success": False,
            "message": "total_deposit must be a valid decimal",
            "error": "total_deposit must be a valid decimal",
        }

    operator_party = await party_service.get_party(db, party_id=operator_party_id)
    if operator_party is None:
        return {
            "success": False,
            "message": "Operator party not found",
            "error": "Operator party not found",
        }

    owner_party = await party_service.get_party(db, party_id=owner_party_id)
    if owner_party is None:
        return {
            "success": False,
            "message": "Owner party not found",
            "error": "Owner party not found",
        }

    try:
        group_payload = ContractGroupCreate(
            revenue_mode=revenue_mode,
            operator_party_id=operator_party_id,
            owner_party_id=owner_party_id,
            effective_from=effective_from,
            effective_to=effective_to,
            settlement_rule=SettlementRuleSchema(**settlement_rule_data),
            revenue_attribution_rule=merged_data.get("revenue_attribution_rule"),
            revenue_share_rule=merged_data.get("revenue_share_rule"),
            risk_tags=merged_data.get("risk_tags"),
            predecessor_group_id=_normalize_text(
                merged_data.get("predecessor_group_id")
            ),
            asset_ids=asset_ids,
        )

        lease_detail: LeaseDetailCreate | None = None
        agency_detail: AgencyDetailCreate | None = None
        if revenue_mode == RevenueMode.LEASE:
            payment_cycle = _normalize_text(merged_data.get("payment_cycle"))
            lease_detail = LeaseDetailCreate(
                total_deposit=total_deposit,
                rent_amount=monthly_rent_base,
                monthly_rent_base=monthly_rent_base,
                payment_cycle=payment_cycle or group_payload.settlement_rule.cycle,
                payment_terms=_normalize_text(merged_data.get("payment_terms")),
                tenant_name=_normalize_text(merged_data.get("tenant_name")),
                tenant_contact=_normalize_text(merged_data.get("tenant_contact")),
                tenant_phone=_normalize_text(merged_data.get("tenant_phone")),
                tenant_address=_normalize_text(merged_data.get("tenant_address")),
            )
        else:
            agency_detail_data = merged_data.get("agency_detail")
            if not isinstance(agency_detail_data, dict):
                return {
                    "success": False,
                    "message": "AGENCY confirm requires agency_detail to be provided explicitly",
                    "error": "AGENCY confirm requires agency_detail to be provided explicitly",
                }
            agency_detail = AgencyDetailCreate(**agency_detail_data)

        group_code = await contract_group_service.generate_group_code(
            db,
            operator_party_id=operator_party_id,
            operator_party_code=operator_party.code,
        )
        created_group = await contract_group_service.create_contract_group(
            db,
            obj_in=group_payload,
            group_code=group_code,
            current_user=str(user_id),
            commit=False,
        )

        contract_payload = ContractCreate(
            contract_group_id=created_group.contract_group_id,
            contract_number=contract_number,
            contract_direction=contract_direction,
            group_relation_type=group_relation_type,
            lessor_party_id=lessor_party_id,
            lessee_party_id=lessee_party_id,
            sign_date=sign_date,
            effective_from=effective_from,
            effective_to=effective_to,
            contract_notes=_normalize_text(merged_data.get("contract_notes")),
            source_session_id=session_id,
            asset_ids=asset_ids,
            lease_detail=lease_detail,
            agency_detail=agency_detail,
        )
        created_contract = await contract_group_service.add_contract_to_group(
            db,
            obj_in=contract_payload,
            current_user=str(user_id),
            commit=False,
        )

        created_terms_count = 0
        rent_terms = merged_data.get("rent_terms")
        if isinstance(rent_terms, list):
            for index, rent_term in enumerate(rent_terms, start=1):
                if not isinstance(rent_term, dict):
                    continue
                rent_term_start = _parse_date(rent_term.get("start_date"))
                rent_term_end = _parse_date(rent_term.get("end_date"))
                rent_term_amount = _parse_decimal(rent_term.get("monthly_rent"))
                management_fee = _parse_decimal(
                    rent_term.get("management_fee"), Decimal("0")
                )
                other_fees = _parse_decimal(rent_term.get("other_fees"), Decimal("0"))
                if (
                    rent_term_start is None
                    or rent_term_end is None
                    or rent_term_amount is None
                    or management_fee is None
                    or other_fees is None
                ):
                    return {
                        "success": False,
                        "message": "Invalid rent_terms payload",
                        "error": "Invalid rent_terms payload",
                    }
                await contract_group_service.create_rent_term(
                    db,
                    contract_id=created_contract.contract_id,
                    obj_in=ContractRentTermCreate(
                        sort_order=index,
                        start_date=rent_term_start,
                        end_date=rent_term_end,
                        monthly_rent=rent_term_amount,
                        management_fee=management_fee,
                        other_fees=other_fees,
                        notes=_normalize_text(
                            rent_term.get("rent_description") or rent_term.get("notes")
                        ),
                    ),
                    commit=False,
                )
                created_terms_count += 1

        processing_result = dict(import_session.processing_result or {})
        processing_result["created_contract_group_id"] = created_group.contract_group_id
        processing_result["created_contract_id"] = created_contract.contract_id
        processing_result["created_terms_count"] = created_terms_count

        import_session.status = SessionStatus.CONFIRMED
        import_session.current_step = ProcessingStep.FINAL_REVIEW
        import_session.progress_percentage = 100.0
        import_session.processing_result = processing_result
        import_session.completed_at = utcnow_naive()

        await db.commit()
        await db.refresh(import_session)

        return {
            "success": True,
            "message": "合同导入成功",
            "contract_group_id": created_group.contract_group_id,
            "contract_id": created_contract.contract_id,
            "contract_number": contract_number,
            "created_terms_count": created_terms_count,
        }
    except ValidationError as exc:
        await db.rollback()
        logger.warning(
            "PDF contract confirm validation failed for session %s: %s",
            session_id,
            exc,
        )
        return {
            "success": False,
            "message": "Confirmed data validation failed",
            "error": "Confirmed data validation failed",
        }
    except BaseBusinessError as exc:
        await db.rollback()
        logger.warning(
            "PDF contract confirm business validation failed for session %s: %s",
            session_id,
            exc,
        )
        return {"success": False, "message": str(exc), "error": str(exc)}
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "PDF contract confirm failed for session %s",
            session_id,
        )
        return {
            "success": False,
            "message": "Contract import confirm failed",
            "error": str(exc),
        }
