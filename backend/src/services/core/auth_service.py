"""
[DEPRECATED] This module is deprecated.
Please use specialized services in this directory:
- authentication_service.py
- user_management_service.py
- password_service.py
- session_service.py
- audit_service.py
"""

from sqlalchemy.orm import Session

from ...models.auth import User, AuditLog, UserSession
from ...schemas.auth import UserCreate, UserUpdate, TokenResponse
from .authentication_service import AuthenticationService
from .user_management_service import UserManagementService
from .password_service import PasswordService
from .session_service import SessionService
from .audit_service import AuditService

UserCreate = UserCreate
UserUpdate = UserUpdate
TokenResponse = TokenResponse
UserSessionResponse = object # Placeholder if needed, or import if available

class AuthService:
    """
    Deprecated monolithic service.
    Delegates calls to new specialized services.
    """
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthenticationService(db)
        self.user_service = UserManagementService(db)
        self.password_service = PasswordService()
        self.session_service = SessionService(db)
        self.audit_service = AuditService(db)

    # --- Authentication Delegate ---
    def authenticate_user(self, username, password):
        return self.auth_service.authenticate_user(username, password)

    def create_tokens(self, user, device_info=None):
        return self.auth_service.create_tokens(user, device_info)

    def validate_refresh_token(self, refresh_token, client_ip=None, user_agent=None):
        return self.auth_service.validate_refresh_token(refresh_token, client_ip, user_agent)

    # --- User Management Delegate ---
    def create_user(self, user_data):
        return self.user_service.create_user(user_data)

    def get_user_by_id(self, user_id):
        return self.user_service.get_user_by_id(user_id)

    def get_user_by_username(self, username):
        return self.user_service.get_user_by_username(username)

    def get_user_by_email(self, email):
        return self.user_service.get_user_by_email(email)

    def update_user(self, user_id, user_data):
        return self.user_service.update_user(user_id, user_data)

    def deactivate_user(self, user_id):
        return self.user_service.deactivate_user(user_id)

    def activate_user(self, user_id):
        return self.user_service.activate_user(user_id)

    def unlock_user(self, user_id):
        return self.user_service.unlock_user(user_id)

    def change_password(self, user, current_password, new_password):
        return self.user_service.change_password(user, current_password, new_password)

    # --- Session Delegate ---
    def create_user_session(self, *args, **kwargs):
        return self.session_service.create_user_session(*args, **kwargs)

    def get_user_sessions(self, user_id):
        # The original return type needs to be mapped if it was Pydantic models
        # For now returning ORM objects as SessionService does
        # If API expects Pydantic, the router handles conversion usually
        from ...schemas.auth import UserSessionResponse
        sessions = self.session_service.get_user_sessions(user_id)
        return [UserSessionResponse.from_orm(s) for s in sessions]

    def revoke_session(self, refresh_token):
        return self.session_service.revoke_session(refresh_token)

    def revoke_all_user_sessions(self, user_id):
        return self.session_service.revoke_all_user_sessions(user_id)

    # --- Password Delegate ---
    def verify_password(self, plain, hashed):
        return self.password_service.verify_password(plain, hashed)

    def get_password_hash(self, password):
        return self.password_service.get_password_hash(password)

    def validate_password_strength(self, password):
        return self.password_service.validate_password_strength(password)

    def is_password_in_history(self, user, password):
        return self.password_service.is_password_in_history(user, password)

    def add_password_to_history(self, user, password_hash):
        return self.password_service.add_password_to_history(user, password_hash)

    def is_password_expired(self, user):
        return self.password_service.is_password_expired(user)

    # --- Audit Delegate ---
    def create_audit_log(self, *args, **kwargs):
        return self.audit_service.create_audit_log(*args, **kwargs)

    # Internal helpers expose if needed
    def _generate_jti(self):
        return self.auth_service._generate_jti()

    def _is_token_revoked(self, jti):
        return self.auth_service._is_token_revoked(jti)
