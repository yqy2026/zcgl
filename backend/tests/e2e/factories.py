"""
Shared E2E test data factories.
"""

from src.models.ownership import Ownership


def _create_ownership(
    db_session,
    *,
    suffix: str,
    name_prefix: str,
    code_prefix: str,
    short_prefix: str,
) -> Ownership:
    ownership = Ownership(
        name=f"{name_prefix}-{suffix}",
        code=f"{code_prefix}-{suffix}",
        short_name=f"{short_prefix}{suffix[:4]}",
        data_status="正常",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    return ownership


def create_asset_ownership(db_session, suffix: str) -> Ownership:
    return _create_ownership(
        db_session,
        suffix=suffix,
        name_prefix="E2E权属方",
        code_prefix="E2E-OWN",
        short_prefix="E2E",
    )


def create_contract_ownership(db_session, suffix: str) -> Ownership:
    return _create_ownership(
        db_session,
        suffix=suffix,
        name_prefix="E2E合同权属方",
        code_prefix="E2E-CON-OWN",
        short_prefix="EC",
    )


def create_asset_payload(
    *,
    suffix: str,
    ownership_id: str,
    usage_status: str = "出租",
    name_prefix: str = "E2E资产",
    address_prefix: str = "E2E地址",
    business_prefix: str = "E2E业态",
    created_by: str = "e2e_test",
) -> dict[str, object]:
    return {
        "ownership_id": ownership_id,
        "asset_name": f"{name_prefix}-{suffix}",
        "address": f"{address_prefix}-{suffix}",
        "ownership_status": "已确权",
        "property_nature": "经营类",
        "usage_status": usage_status,
        "business_category": f"{business_prefix}-{suffix}",
        "data_status": "正常",
        "created_by": created_by,
    }


def create_contract_asset_payload(*, suffix: str, ownership_id: str) -> dict[str, object]:
    return create_asset_payload(
        suffix=suffix,
        ownership_id=ownership_id,
        usage_status="出租",
        name_prefix="E2E合同资产",
        address_prefix="E2E合同资产地址",
        business_prefix="E2E合同业态",
        created_by="e2e_contract_test",
    )


def create_contract_payload(*, suffix: str, ownership_id: str) -> dict[str, object]:
    return {
        "contract_number": f"E2E-CON-{suffix}",
        "contract_type": "lease_downstream",
        "tenant_name": f"E2E租户-{suffix}",
        "tenant_contact": "张三",
        "tenant_phone": "13800138000",
        "tenant_usage": "办公",
        "asset_ids": [],
        "ownership_id": ownership_id,
        "sign_date": "2026-01-01",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "total_deposit": 10000,
        "monthly_rent_base": 5000,
        "payment_cycle": "monthly",
        "rent_terms": [
            {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "monthly_rent": 5000,
            }
        ],
    }
