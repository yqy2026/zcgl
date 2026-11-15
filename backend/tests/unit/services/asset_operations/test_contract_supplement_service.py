import pytest
from pydantic import ValidationError

from src.schemas.contract_supplement import SupplementCreate

pytestmark = pytest.mark.unit


def test_registration_rejects_blank_number():
    with pytest.raises(ValidationError):
        SupplementCreate(
            contract_kind="upstream",
            contract_id="c",
            agreement_number=" ",
            title="协议",
        )


def test_registration_normalizes_business_text():
    item = SupplementCreate(
        contract_kind="terminal",
        contract_id="c",
        agreement_number=" A ",
        title=" 名称 ",
    )
    assert item.agreement_number == "A"
    assert item.title == "名称"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_scope_rejects_before_contract_query():
    from unittest.mock import AsyncMock

    from src.core.exception_handler import PartyScopeForbiddenError
    from src.services.asset_operations.contract_supplement_service import (
        contract_supplement_service,
    )
    from src.services.party_scope_resolver import EffectivePartyScope

    db = AsyncMock()
    with pytest.raises(PartyScopeForbiddenError):
        await contract_supplement_service.list(
            db,
            kind="upstream",
            contract_id="hidden",
            scope=EffectivePartyScope(
                user_id="actor", source="explicit", scope_mode="owner"
            ),
        )
    db.execute.assert_not_awaited()


def test_withdrawal_rejects_blank_reason():
    from src.schemas.contract_supplement import SupplementWithdrawal

    with pytest.raises(ValidationError):
        SupplementWithdrawal(expected_version=1, reason="  ")
