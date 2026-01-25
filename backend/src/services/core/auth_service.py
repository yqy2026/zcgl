"""
[DEPRECATED] This module is deprecated.
Please use specialized services in this directory:
- authentication_service.py
- user_management_service.py
- password_service.py
- session_service.py
- audit_service.py
"""

from typing import Any

from sqlalchemy.orm import Session

from ...models.auth import User
from ...schemas.auth import TokenResponse, UserCreate, UserUpdate
from .audit_service import AuditService
from .authentication_service import AuthenticationService
from .password_service import PasswordService
from .session_service import SessionService
from .user_management_service import UserManagementService

UserCreate = UserCreate
UserUpdate = UserUpdate
TokenResponse = TokenResponse
UserSessionResponse = object  # Placeholder if needed, or import if available


class AuthService:
    """
    Deprecated monolithic service.
    Delegates calls to new specialized services.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthenticationService(db)
        self.user_service = UserManagementService(db)
        self.password_service = PasswordService()
        self.session_service = SessionService(db)
        self.audit_service = AuditService(db)

    # --- Authentication Delegate ---
    def authenticate_user(self, username: str, password: str) -> User | None:
        return self.auth_service.authenticate_user(username, password)

    def create_tokens(
        self, user: User, device_info: dict[str, Any] | str | None = None
    ) -> TokenResponse:
        # Accept both dict (new format) and str (legacy format) for compatibility
        device_info_dict = (
            device_info
            if isinstance(device_info, dict)
            else {"user_agent": device_info}
            if device_info
            else None
        )
        return self.auth_service.create_tokens(user, device_info_dict)

    def validate_refresh_token(
        self,
        refresh_token: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> User | None:
        from ...models.auth import UserSession

        result: Any = self.auth_service.validate_refresh_token(
            refresh_token, client_ip, user_agent
        )
        # Extract User from UserSession if needed
        if isinstance(result, UserSession):
            return result.user
        if isinstance(result, User):
            return result
        return None

    # --- User Management Delegate ---
    def create_user(self, user_data: UserCreate) -> User:
        return self.user_service.create_user(user_data)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.user_service.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        return self.user_service.get_user_by_username(username)

    def get_user_by_email(self, email: str) -> User | None:
        return self.user_service.get_user_by_email(email)

    def update_user(self, user_id: str, user_data: UserUpdate) -> User | None:
        return self.user_service.update_user(user_id, user_data)

    def deactivate_user(self, user_id: str) -> bool:
        return self.user_service.deactivate_user(user_id)

    def activate_user(self, user_id: str) -> bool:
        return self.user_service.activate_user(user_id)

    def unlock_user(self, user_id: str) -> bool:
        return self.user_service.unlock_user(user_id)

    def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> bool:
        return self.user_service.change_password(user, current_password, new_password)

    # --- Session Delegate ---
    def create_user_session(self, *args: Any, **kwargs: Any) -> Any:
        return self.session_service.create_user_session(*args, **kwargs)

    def get_user_sessions(self, user_id: str) -> list[Any]:
        # The original return type needs to be mapped if it was Pydantic models
        # For now returning ORM objects as SessionService does
        # If API expects Pydantic, the router handles conversion usually
        from ...schemas.auth import UserSessionResponse

        sessions = self.session_service.get_user_sessions(user_id)
        return [UserSessionResponse.from_orm(s) for s in sessions]

    def revoke_session(self, refresh_token: str) -> bool:
        return self.session_service.revoke_session(refresh_token)

    def revoke_all_user_sessions(self, user_id: str) -> int:
        return self.session_service.revoke_all_user_sessions(user_id)

    # --- Password Delegate ---
    def verify_password(self, plain: str, hashed: str) -> bool:
        return self.password_service.verify_password(plain, hashed)

    def get_password_hash(self, password: str) -> str:
        return self.password_service.get_password_hash(password)

    def validate_password_strength(self, password: str) -> bool:
        return self.password_service.validate_password_strength(password)

    def is_password_in_history(self, user: User, password: str) -> bool:
        return self.password_service.is_password_in_history(user, password)

    def add_password_to_history(self, user: User, password_hash: str) -> None:
        return self.password_service.add_password_to_history(user, password_hash)

    def is_password_expired(self, user: User) -> bool:
        return self.password_service.is_password_expired(user)

    # --- Audit Delegate ---
    def create_audit_log(self, *args: Any, **kwargs: Any) -> Any:
        return self.audit_service.create_audit_log(*args, **kwargs)

    # Internal helpers expose if needed
    def _generate_jti(self) -> str:
        return self.auth_service._generate_jti()

    def _is_token_revoked(self, jti: str) -> bool:
        return self.auth_service._is_token_revoked(jti)
