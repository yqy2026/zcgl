"""Dev-database walkthrough seed: user, RBAC, and minimal v5 facts.

Idempotent, fixed IDs, dev only. Run: uv run --frozen --extra dev python scripts/dev_seed_v5_walkthrough.py
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime
from decimal import Decimal

USER_ID = "v5-walkthrough-user"
OWNER_ID = "v5-walkthrough-owner"
OPERATOR_ID = "v5-walkthrough-operator"
TENANT_ID = "v5-walkthrough-tenant"
PROJECT_ID = "v5-walkthrough-project"
UNIT_A = "v5-walkthrough-unit-a"
UNIT_B = "v5-walkthrough-unit-b"
OTHER_OWNER_UNIT = "v5-walkthrough-other-owner-unit"
UPSTREAM_ID = "v5-walkthrough-upstream"
TERMINAL_ID = "v5-walkthrough-terminal"
MGMT_ID = "v5-walkthrough-mgmt"
FEE_TERMINAL_ID = "v5-walkthrough-terminal-owner"
SCAN_MGMT = "v5-walkthrough-scan-mgmt"
SCAN_FEE_TM = "v5-walkthrough-scan-fee-tm"
SCAN_UP = "v5-walkthrough-scan-up"
SCAN_TM = "v5-walkthrough-scan-tm"
USERNAME = "v5-walkthrough"
PASSWORD = os.environ.get("V5_WALKTHROUGH_PASSWORD", "")


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from src.database import get_async_database_url
    from src.models.asset_contract import (
        ContractRentSchedule,
        TerminalContract,
        TerminalContractAssetUnit,
        UpstreamContract,
        UpstreamContractAssetUnit,
    )
    from src.models.asset_unit import AssetUnit
    from src.models.attachment import Attachment
    from src.models.auth import AccountType, User
    from src.models.party import Party, PartyReviewStatus, PartyType
    from src.models.project import Project
    from src.models.rbac import Role, UserRoleAssignment
    from src.services.core.password_service import PasswordService

    engine = create_async_engine(get_async_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    password_service = PasswordService()

    async with factory() as session:
        party = await session.get(Party, OWNER_ID)
        if party is None:
            session.add_all(
                [
                    Party(
                        id=OWNER_ID,
                        party_type=PartyType.LEGAL_ENTITY,
                        name="走查产权方",
                        code="LE-990101",
                        status="active",
                        review_status=PartyReviewStatus.APPROVED,
                    ),
                    Party(
                        id=OPERATOR_ID,
                        party_type=PartyType.LEGAL_ENTITY,
                        name="走查运营方",
                        code="LE-990102",
                        status="active",
                        review_status=PartyReviewStatus.APPROVED,
                    ),
                    Party(
                        id=TENANT_ID,
                        party_type=PartyType.LEGAL_ENTITY,
                        name="走查租户",
                        code="LE-990103",
                        status="active",
                        review_status=PartyReviewStatus.APPROVED,
                    ),
                ]
            )
            await session.flush()
            session.add(
                Project(
                    id=PROJECT_ID,
                    project_name="走查项目",
                    project_code="PRJ-V5-WALKTHROUGH",
                    status="active",
                    manager_party_id=OPERATOR_ID,
                )
            )
            await session.flush()
            session.add_all(
                [
                    AssetUnit(
                        id=UNIT_A,
                        unit_code="AU-WALK-A",
                        name="走查单元 A",
                        project_id=PROJECT_ID,
                        owner_party_id=OWNER_ID,
                        address="走查地址 1 号",
                        usage_type="commercial",
                        acquisition_mode="leased",
                        is_operating=True,
                        land_area=Decimal("0"),
                        building_area=Decimal("100"),
                        rentable_area=Decimal("80"),
                        managed_from=date(2026, 1, 1),
                        predecessor_unit_ids=[],
                        version=1,
                    ),
                    AssetUnit(
                        id=UNIT_B,
                        unit_code="AU-WALK-B",
                        name="走查单元 B",
                        project_id=PROJECT_ID,
                        owner_party_id=OWNER_ID,
                        address="走查地址 2 号",
                        usage_type="commercial",
                        acquisition_mode="leased",
                        is_operating=True,
                        land_area=Decimal("0"),
                        building_area=Decimal("60"),
                        rentable_area=Decimal("50"),
                        managed_from=date(2026, 1, 1),
                        predecessor_unit_ids=[],
                        version=1,
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Attachment(
                        id=SCAN_UP,
                        owner_type="contract",
                        owner_id=UPSTREAM_ID,
                        file_name="walk-upstream.pdf",
                        file_type="pdf",
                        file_size=1,
                        storage_key="walkthrough/upstream.pdf",
                        created_by=USER_ID,
                    ),
                    Attachment(
                        id=SCAN_TM,
                        owner_type="contract",
                        owner_id=TERMINAL_ID,
                        file_name="walk-terminal.pdf",
                        file_type="pdf",
                        file_size=1,
                        storage_key="walkthrough/terminal.pdf",
                        created_by=USER_ID,
                    ),
                ]
            )
            await session.flush()
            session.add(
                UpstreamContract(
                    id=UPSTREAM_ID,
                    contract_number="UP-WALK-001",
                    contract_type="lease",
                    name="走查上游承租合同",
                    owner_party_id=OWNER_ID,
                    operator_party_id=OPERATOR_ID,
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 12, 31),
                    payment_cycle="monthly",
                    payment_day=15,
                    deposit_amount=Decimal("50000"),
                    scan_document_id=SCAN_UP,
                    version=1,
                ),
            )
            await session.flush()
            session.add(
                TerminalContract(
                    id=TERMINAL_ID,
                    contract_number="TM-WALK-001",
                    contract_mode="sublease",
                    tenant_party_id=TENANT_ID,
                    lessor_party_id=OPERATOR_ID,
                    upstream_contract_id=UPSTREAM_ID,
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 6, 30),
                    deposit_amount=Decimal("20000"),
                    rent_collector="operator",
                    scan_document_id=SCAN_TM,
                    version=1,
                )
            )
            await session.flush()
            session.add_all(
                [
                    UpstreamContractAssetUnit(
                        upstream_contract_id=UPSTREAM_ID,
                        asset_unit_id=UNIT_A,
                        effective_from=date(2026, 1, 1),
                        effective_to=date(2027, 12, 31),
                    ),
                    UpstreamContractAssetUnit(
                        upstream_contract_id=UPSTREAM_ID,
                        asset_unit_id=UNIT_B,
                        effective_from=date(2026, 1, 1),
                        effective_to=date(2027, 12, 31),
                    ),
                    TerminalContractAssetUnit(
                        terminal_contract_id=TERMINAL_ID,
                        asset_unit_id=UNIT_A,
                        effective_from=date(2026, 1, 1),
                        effective_to=date(2027, 6, 30),
                    ),
                ]
            )
            print("v5 facts seeded")

        # Keep an actual out-of-scope record so Party isolation assertions cannot
        # pass merely because the other owner's inventory is empty. This must
        # also work when the original walkthrough facts have already been seeded.
        if await session.get(AssetUnit, OTHER_OWNER_UNIT) is None:
            session.add(
                AssetUnit(
                    id=OTHER_OWNER_UNIT,
                    unit_code="AU-WALK-OTHER",
                    name="走查其他产权方单元",
                    project_id=PROJECT_ID,
                    owner_party_id=OPERATOR_ID,
                    address="走查地址 3 号",
                    usage_type="commercial",
                    acquisition_mode="owned",
                    is_operating=True,
                    land_area=Decimal("0"),
                    building_area=Decimal("40"),
                    rentable_area=Decimal("30"),
                    managed_from=date(2026, 1, 1),
                    predecessor_unit_ids=[],
                    version=1,
                )
            )
            print("v5 other-owner fact seeded")

        user = await session.get(User, USER_ID)
        if user is None:
            user = User(
                id=USER_ID,
                username=USERNAME,
                email="v5-walkthrough@example.com",
                phone="13900007777",
                full_name="V5 走查用户",
                password_hash=password_service.get_password_hash(PASSWORD),
                password_last_changed=datetime.now(UTC).replace(tzinfo=None),
                account_type=AccountType.SYSTEM,
            )
            session.add(user)
            print("user created")
        else:
            user.password_hash = password_service.get_password_hash(PASSWORD)
            user.password_last_changed = datetime.now(UTC).replace(tzinfo=None)
            print("user refreshed")

        role = await session.scalar(select(Role).where(Role.name == "system_admin"))
        if role is None:
            role = Role(
                id="role-v5-walkthrough-admin",
                name="system_admin",
                description="走查用系统管理员",
            )
            session.add(role)
            await session.flush()
            print("role created")
        assignment = await session.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == USER_ID,
                UserRoleAssignment.role_id == role.id,
            )
        )
        if assignment is None:
            session.add(UserRoleAssignment(user_id=USER_ID, role_id=role.id))
            print("role assigned")

        # Management fee chain: a management agreement plus an owner-collected
        # direct lease. Seeded after the user because the replan hook writes
        # obligations and audit rows that reference users.id. Fee statements
        # themselves come from the production replan hook, never from direct
        # statement inserts.
        if await session.get(UpstreamContract, MGMT_ID) is None:
            session.add(
                Attachment(
                    id=SCAN_MGMT,
                    owner_type="contract",
                    owner_id=MGMT_ID,
                    file_name="walk-mgmt.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="walkthrough/mgmt.pdf",
                    created_by=USER_ID,
                )
            )
            await session.flush()
            session.add(
                UpstreamContract(
                    id=MGMT_ID,
                    contract_number="UP-WALK-MGMT",
                    contract_type="management_agreement",
                    name="走查委托管理协议",
                    owner_party_id=OWNER_ID,
                    operator_party_id=OPERATOR_ID,
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 12, 31),
                    deposit_amount=Decimal("0"),
                    management_fee_rate=Decimal("0.10"),
                    scan_document_id=SCAN_MGMT,
                    version=1,
                ),
            )
            session.add(
                UpstreamContractAssetUnit(
                    upstream_contract_id=MGMT_ID,
                    asset_unit_id=UNIT_B,
                    effective_from=date(2026, 1, 1),
                    effective_to=date(2027, 12, 31),
                )
            )
        if await session.get(TerminalContract, FEE_TERMINAL_ID) is None:
            session.add(
                Attachment(
                    id=SCAN_FEE_TM,
                    owner_type="contract",
                    owner_id=FEE_TERMINAL_ID,
                    file_name="walk-fee-terminal.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="walkthrough/fee-terminal.pdf",
                    created_by=USER_ID,
                )
            )
            await session.flush()
            session.add(
                TerminalContract(
                    id=FEE_TERMINAL_ID,
                    contract_number="TM-WALK-OWNER",
                    contract_mode="direct_lease",
                    tenant_party_id=TENANT_ID,
                    lessor_party_id=OWNER_ID,
                    upstream_contract_id=MGMT_ID,
                    start_date=date(2026, 1, 1),
                    end_date=date(2027, 6, 30),
                    deposit_amount=Decimal("0"),
                    rent_collector="owner",
                    scan_document_id=SCAN_FEE_TM,
                    version=1,
                )
            )
            session.add(
                TerminalContractAssetUnit(
                    terminal_contract_id=FEE_TERMINAL_ID,
                    asset_unit_id=UNIT_B,
                    effective_from=date(2026, 1, 1),
                    effective_to=date(2027, 6, 30),
                )
            )
            session.add(
                ContractRentSchedule(
                    contract_kind="terminal",
                    contract_id=FEE_TERMINAL_ID,
                    stage_start=date(2026, 1, 1),
                    stage_end=date(2027, 6, 30),
                    base_monthly_rent=Decimal("10000"),
                    actual_monthly_rent=Decimal("10000"),
                    payment_cycle="monthly",
                    due_day=15,
                )
            )
            await session.flush()
            from uuid import uuid4

            from src.services.asset_operations.rent_obligation_service import (
                rent_obligation_service,
            )

            await rent_obligation_service.replan(
                session,
                contract_kind="terminal",
                contract_id=FEE_TERMINAL_ID,
                actor_id=USER_ID,
                correlation_id=str(uuid4()),
            )
            print("v5 management fee facts seeded")

        await session.commit()
    await engine.dispose()
    print("seed done")


if __name__ == "__main__":
    asyncio.run(main())
