from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import BusinessLogicError
from src.services.core.authentication_service import AsyncAuthenticationService

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_expired_password_requires_valid_current_credentials_and_revokes_sessions():
    db = MagicMock(commit=AsyncMock())
    passwords = MagicMock()
    passwords.is_password_expired.return_value = True
    passwords.verify_password.return_value = False
    users = MagicMock(change_password=AsyncMock(return_value=True))
    service = AsyncAuthenticationService(
        db, password_service=passwords, user_service=users, session_service=MagicMock()
    )
    user = MagicMock()
    service.authenticate_user = AsyncMock(return_value=user)
    await service.change_expired_password("admin", "old", "NewStrong!123")
    service.authenticate_user.assert_awaited_once_with(
        "admin", "old", allow_expired=True
    )
    users.change_password.assert_awaited_once_with(user, "old", "NewStrong!123")


async def test_nonexpired_password_cannot_use_expired_entry():
    passwords = MagicMock()
    passwords.is_password_expired.return_value = False
    users = MagicMock(change_password=AsyncMock())
    service = AsyncAuthenticationService(
        MagicMock(),
        password_service=passwords,
        user_service=users,
        session_service=MagicMock(),
    )
    service.authenticate_user = AsyncMock(return_value=MagicMock())
    with pytest.raises(BusinessLogicError):
        await service.change_expired_password("admin", "old", "NewStrong!123")
    users.change_password.assert_not_called()


@pytest.mark.parametrize("locked", [False, True])
async def test_invalid_or_locked_credentials_never_change_password(locked):
    from src.core.exception_handler import BaseBusinessError

    users = MagicMock(change_password=AsyncMock())
    service = AsyncAuthenticationService(
        MagicMock(),
        password_service=MagicMock(),
        user_service=users,
        session_service=MagicMock(),
    )
    service.authenticate_user = AsyncMock(
        side_effect=BusinessLogicError("locked") if locked else None,
        return_value=None,
    )
    with pytest.raises(BaseBusinessError) as caught:
        await service.change_expired_password("user", "wrong", "NewStrong!123")
    assert caught.value.status_code == 401
    users.change_password.assert_not_called()


async def test_empty_password_history_still_remembers_previous_password():
    from src.models.auth import User
    from src.services.core.password_service import PasswordService
    from src.services.core.user_management_service import AsyncUserManagementService

    passwords = PasswordService()
    user = User(
        id="test-user",
        password_hash=passwords.get_password_hash("OldPassword!2026"),
        password_history=None,
    )
    service = AsyncUserManagementService(
        MagicMock(commit=AsyncMock()),
        password_service=passwords,
        session_service=MagicMock(revoke_all_user_sessions=AsyncMock()),
        rbac_service=MagicMock(),
    )
    await service.change_password(user, "OldPassword!2026", "NewPassword!2026")
    assert passwords.is_password_in_history(user, "OldPassword!2026")
    assert passwords.is_password_in_history(user, "NewPassword!2026")
