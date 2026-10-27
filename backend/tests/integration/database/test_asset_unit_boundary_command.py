"""PostgreSQL integration coverage for asset-unit boundary commands."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.crud.asset_unit import asset_unit_repository
from src.crud.asset_unit_boundary import asset_unit_boundary_repository
from src.database import get_async_database_url
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.asset_unit import (
    AssetUnit,
    AssetUnitBoundaryChange,
    AssetUnitBoundarySource,
)
from src.models.attachment import Attachment
from src.models.auth import AccountType, User
from src.models.party import Party, PartyReviewStatus, PartyType
from src.models.project import Project
from src.schemas.asset_operations import (
    AssetUnitMergeCommitRequest,
    AssetUnitMergeProposal,
    AssetUnitMergeResultInput,
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPartInput,
    AssetUnitSplitProposal,
)
from src.services.asset_operations.boundary_command_service import (
    AssetUnitBoundaryCommandService,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.fixtures.fake_credentials import fake_bcrypt_hash

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.asyncio]

ACTOR_ID = "asset-ops-integration-actor"
OWNER_ID = "asset-ops-integration-owner"
PROJECT_ID = "asset-ops-integration-project"
SOURCE_ID = "asset-ops-integration-source"
SOURCE_CODE = "AU-INT-SOURCE"
RESULT_CODES = ("AU-INT-RESULT-A", "AU-INT-RESULT-B")
MERGE_SOURCE_ID = "asset-ops-integration-merge-source"
MERGE_SOURCE_CODE = "AU-INT-MERGE-SOURCE"
MERGE_RESULT_CODE = "AU-INT-MERGED"
UPSTREAM_ID = "asset-ops-integration-upstream"
ATTACHMENT_ID = "asset-ops-integration-attachment"


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        get_async_database_url(),
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def reset_facts() -> None:
        async with factory() as session:
            await session.execute(
                delete(AssetUnitBoundarySource).where(
                    AssetUnitBoundarySource.asset_unit_id.in_(
                        select(AssetUnit.id).where(AssetUnit.project_id == PROJECT_ID)
                    )
                )
            )
            await session.execute(
                delete(AssetUnitBoundaryChange).where(
                    AssetUnitBoundaryChange.created_by == ACTOR_ID
                )
            )
            await session.execute(
                delete(AssetUnit).where(AssetUnit.project_id == PROJECT_ID)
            )
            await session.execute(
                delete(UpstreamContract).where(UpstreamContract.id == UPSTREAM_ID)
            )
            await session.execute(
                delete(Attachment).where(Attachment.id == ATTACHMENT_ID)
            )
            await session.execute(delete(Project).where(Project.id == PROJECT_ID))
            await session.execute(delete(Party).where(Party.id == OWNER_ID))
            await session.execute(delete(User).where(User.id == ACTOR_ID))
            await session.commit()

    await reset_facts()
    try:
        yield factory
    finally:
        await reset_facts()
        await engine.dispose()


async def _seed_source(
    factory: async_sessionmaker[AsyncSession],
) -> EffectivePartyScope:
    async with factory() as session:
        session.add_all(
            [
                User(
                    id=ACTOR_ID,
                    username="asset_ops_integration_actor",
                    email="asset-ops-integration@example.test",
                    phone="13900009001",
                    full_name="资产运营集成测试操作者",
                    password_hash=fake_bcrypt_hash(),
                    account_type=AccountType.SYSTEM,
                ),
                Party(
                    id=OWNER_ID,
                    party_type=PartyType.LEGAL_ENTITY,
                    name="资产运营集成测试产权方",
                    code="LE-990001",
                    status="active",
                    review_status=PartyReviewStatus.APPROVED,
                ),
            ]
        )
        await session.flush()
        session.add(
            Project(
                id=PROJECT_ID,
                project_name="资产运营集成测试项目",
                project_code="PRJ-ASSET-OPS-INTEGRATION",
                status="active",
                manager_party_id=OWNER_ID,
            )
        )
        await session.flush()
        session.add(
            AssetUnit(
                id=SOURCE_ID,
                unit_code=SOURCE_CODE,
                name="待拆分资产单元",
                project_id=PROJECT_ID,
                owner_party_id=OWNER_ID,
                address="集成测试地址 1 号",
                usage_type="commercial",
                acquisition_mode="owned",
                is_operating=True,
                land_area=Decimal("100.00"),
                building_area=Decimal("80.00"),
                rentable_area=Decimal("60.00"),
                managed_from=date(2026, 1, 1),
                predecessor_unit_ids=[],
                version=1,
            )
        )
        await session.commit()

    return EffectivePartyScope(
        user_id=ACTOR_ID,
        source="explicit",
        scope_mode="owner",
        owner_party_ids=[OWNER_ID],
    )


def _proposal() -> AssetUnitSplitProposal:
    return AssetUnitSplitProposal(
        source_unit_id=SOURCE_ID,
        effective_date=date(2026, 11, 1),
        parts=[
            AssetUnitSplitPartInput(
                unit_code=RESULT_CODES[0],
                name="拆分结果 A",
                land_area=Decimal("40.00"),
                building_area=Decimal("30.00"),
                rentable_area=Decimal("20.00"),
            ),
            AssetUnitSplitPartInput(
                unit_code=RESULT_CODES[1],
                name="拆分结果 B",
                land_area=Decimal("60.00"),
                building_area=Decimal("50.00"),
                rentable_area=Decimal("40.00"),
            ),
        ],
    )


async def _seed_merge_sources(
    factory: async_sessionmaker[AsyncSession],
) -> EffectivePartyScope:
    scope = await _seed_source(factory)
    async with factory() as session:
        session.add_all(
            [
                AssetUnit(
                    id=MERGE_SOURCE_ID,
                    unit_code=MERGE_SOURCE_CODE,
                    name="待合并资产单元",
                    project_id=PROJECT_ID,
                    owner_party_id=OWNER_ID,
                    address="集成测试地址 1 号",
                    usage_type="commercial",
                    acquisition_mode="owned",
                    is_operating=True,
                    land_area=Decimal("50.00"),
                    building_area=Decimal("40.00"),
                    rentable_area=Decimal("30.00"),
                    managed_from=date(2026, 1, 1),
                    predecessor_unit_ids=[],
                    version=1,
                ),
                Attachment(
                    id=ATTACHMENT_ID,
                    owner_type="contract",
                    owner_id=UPSTREAM_ID,
                    file_name="asset-ops-integration-upstream.pdf",
                    file_type="pdf",
                    file_size=1,
                    storage_key="asset-ops/integration/upstream.pdf",
                    created_by=ACTOR_ID,
                ),
            ]
        )
        await session.flush()
        session.add(
            UpstreamContract(
                id=UPSTREAM_ID,
                contract_number="UP-ASSET-OPS-INTEGRATION",
                contract_type="lease",
                name="资产运营集成测试上游合同",
                owner_party_id=OWNER_ID,
                operator_party_id=OWNER_ID,
                start_date=date(2026, 1, 1),
                end_date=date(2027, 12, 31),
                payment_cycle="monthly",
                payment_day=1,
                deposit_amount=Decimal("0"),
                scan_document_id=ATTACHMENT_ID,
            )
        )
        await session.flush()
        session.add_all(
            [
                UpstreamContractAssetUnit(
                    upstream_contract_id=UPSTREAM_ID,
                    asset_unit_id=unit_id,
                    effective_from=date(2026, 11, 1),
                    effective_to=date(2027, 12, 31),
                )
                for unit_id in (SOURCE_ID, MERGE_SOURCE_ID)
            ]
        )
        await session.commit()
    return scope


async def test_merge_commit_persists_one_result_and_replays(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await _seed_merge_sources(session_factory)
    service = AssetUnitBoundaryCommandService(
        clock=lambda: datetime(2026, 10, 24, 9, 0, 0)
    )
    proposal = AssetUnitMergeProposal(
        source_unit_ids=[MERGE_SOURCE_ID, SOURCE_ID],
        effective_date=date(2026, 11, 1),
        result=AssetUnitMergeResultInput(
            unit_code=MERGE_RESULT_CODE,
            name="合并后的资产单元",
        ),
    )

    async with session_factory() as session:
        preview = await service.preview_merge(
            session,
            proposal=proposal,
            actor_id=ACTOR_ID,
            scope=scope,
        )
        request = AssetUnitMergeCommitRequest(
            preview_token=preview.preview_token,
            reason="恢复完整经营边界",
            expected_versions=preview.versions,
        )
        committed = await service.commit_merge(
            session,
            request=request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="asset-ops-integration-merge-001",
        )
        replayed = await service.commit_merge(
            session,
            request=request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="asset-ops-integration-merge-001",
        )

    assert committed.idempotent is False
    assert replayed.idempotent is True
    assert replayed.boundary_change_id == committed.boundary_change_id
    assert committed.source_unit_ids == [MERGE_SOURCE_ID, SOURCE_ID]
    assert len(committed.result_unit_ids) == 1

    async with session_factory() as observation_session:
        sources = (
            (
                await observation_session.execute(
                    select(AssetUnit)
                    .where(AssetUnit.id.in_((SOURCE_ID, MERGE_SOURCE_ID)))
                    .order_by(AssetUnit.id)
                )
            )
            .scalars()
            .all()
        )
        result = (
            (
                await observation_session.execute(
                    select(AssetUnit).where(AssetUnit.unit_code == MERGE_RESULT_CODE)
                )
            )
            .scalars()
            .one()
        )
        change = await observation_session.get(
            AssetUnitBoundaryChange,
            committed.boundary_change_id,
        )
        source_links = (
            (
                await observation_session.execute(
                    select(AssetUnitBoundarySource).where(
                        AssetUnitBoundarySource.boundary_change_id
                        == committed.boundary_change_id
                    )
                )
            )
            .scalars()
            .all()
        )
        coverages = (
            (
                await observation_session.execute(
                    select(UpstreamContractAssetUnit).where(
                        UpstreamContractAssetUnit.upstream_contract_id == UPSTREAM_ID
                    )
                )
            )
            .scalars()
            .all()
        )

    assert all(source.managed_to == date(2026, 10, 31) for source in sources)
    assert all(source.version == 2 for source in sources)
    assert result.id == committed.result_unit_ids[0]
    assert result.land_area == Decimal("150.00")
    assert result.building_area == Decimal("120.00")
    assert result.rentable_area == Decimal("90.00")
    assert result.predecessor_unit_ids == [MERGE_SOURCE_ID, SOURCE_ID]
    assert change is not None
    assert change.change_type == "merge"
    assert len(source_links) == 2
    source_coverages = [
        coverage
        for coverage in coverages
        if coverage.asset_unit_id in {SOURCE_ID, MERGE_SOURCE_ID}
    ]
    result_coverages = [
        coverage for coverage in coverages if coverage.asset_unit_id == result.id
    ]
    assert source_coverages == []
    assert len(result_coverages) == 1
    assert result_coverages[0].effective_from == date(2026, 11, 1)
    assert result_coverages[0].effective_to == date(2027, 12, 31)


async def test_split_commit_persists_one_atomic_boundary_change_and_replays(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await _seed_source(session_factory)
    service = AssetUnitBoundaryCommandService(
        clock=lambda: datetime(2026, 10, 24, 9, 0, 0)
    )

    async with session_factory() as session:
        preview = await service.preview(
            session,
            proposal=_proposal(),
            actor_id=ACTOR_ID,
            scope=scope,
        )
        request = AssetUnitSplitCommitRequest(
            preview_token=preview.preview_token,
            reason="按运营边界拆分",
            expected_version=1,
        )
        committed = await service.commit(
            session,
            source_unit_id=SOURCE_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="asset-ops-integration-split-001",
        )
        replayed = await service.commit(
            session,
            source_unit_id=SOURCE_ID,
            request=request,
            actor_id=ACTOR_ID,
            scope=scope,
            idempotency_key="asset-ops-integration-split-001",
        )

    assert committed.idempotent is False
    assert replayed.idempotent is True
    assert replayed.boundary_change_id == committed.boundary_change_id
    assert replayed.result_unit_ids == committed.result_unit_ids

    async with session_factory() as observation_session:
        source = await observation_session.get(AssetUnit, SOURCE_ID)
        results = (
            (
                await observation_session.execute(
                    select(AssetUnit)
                    .where(AssetUnit.unit_code.in_(RESULT_CODES))
                    .order_by(AssetUnit.unit_code)
                )
            )
            .scalars()
            .all()
        )
        changes = (
            (
                await observation_session.execute(
                    select(AssetUnitBoundaryChange).where(
                        AssetUnitBoundaryChange.created_by == ACTOR_ID
                    )
                )
            )
            .scalars()
            .all()
        )
        source_links = (
            (
                await observation_session.execute(
                    select(AssetUnitBoundarySource).where(
                        AssetUnitBoundarySource.asset_unit_id == SOURCE_ID
                    )
                )
            )
            .scalars()
            .all()
        )

    assert source is not None
    assert source.managed_to == date(2026, 10, 31)
    assert source.version == 2
    assert len(results) == 2
    assert {result.id for result in results} == set(committed.result_unit_ids)
    assert all(result.project_id == PROJECT_ID for result in results)
    assert all(result.owner_party_id == OWNER_ID for result in results)
    assert all(result.managed_from == date(2026, 11, 1) for result in results)
    assert all(result.predecessor_unit_ids == [SOURCE_ID] for result in results)
    assert len(changes) == 1
    assert changes[0].id == committed.boundary_change_id
    assert len(source_links) == 1
    assert source_links[0].boundary_change_id == committed.boundary_change_id


async def test_boundary_and_contract_coverage_writes_contend_on_same_unit_lock(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await _seed_source(session_factory)

    async with session_factory() as boundary_session:
        context = await asset_unit_boundary_repository.load_split_context(
            boundary_session,
            unit_id=SOURCE_ID,
            scope=scope,
            effective_date=date(2026, 11, 1),
            result_unit_codes=RESULT_CODES,
            for_update=True,
        )
        assert context.source is not None

        async with session_factory() as coverage_session:
            await coverage_session.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(DBAPIError):
                await asset_unit_repository.lock_for_write(
                    coverage_session,
                    unit_ids=[SOURCE_ID],
                    scope=scope,
                )
            await coverage_session.rollback()

        await boundary_session.rollback()

    async with session_factory() as released_session:
        locked = await asset_unit_repository.lock_for_write(
            released_session,
            unit_ids=[SOURCE_ID],
            scope=scope,
        )
        assert [unit.id for unit in locked] == [SOURCE_ID]
        await released_session.rollback()
