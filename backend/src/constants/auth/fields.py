"""
Authentication field name constants.

Provides standardized field names for authentication and
authorization fields throughout the application.
"""

from typing import Final


class AuthFields:
    """
    Authentication and authorization field names.

    These constants define the standard names used for auth-related
    fields in models and schemas.
    """

    # User credentials
    USERNAME: Final[str] = "username"
    EMAIL: Final[str] = "email"
    PASSWORD: Final[str] = "password"
    PHONE: Final[str] = "phone"

    # Authentication tokens
    TOKEN: Final[str] = "token"
    REFRESH_TOKEN: Final[str] = "refresh_token"
    ACCESS_TOKEN: Final[str] = "access_token"
    RESET_TOKEN: Final[str] = "reset_token"

    # User identification
    USER_ID: Final[str] = "user_id"
    USER: Final[str] = "user"

    # Role and permission fields
    ROLE: Final[str] = "role"
    ROLE_ID: Final[str] = "role_id"
    PERMISSIONS: Final[str] = "permissions"
    SCOPES: Final[str] = "scopes"

    # Authentication status
    IS_ACTIVE: Final[str] = "is_active"
    IS_VERIFIED: Final[str] = "is_verified"
    IS_AUTHENTICATED: Final[str] = "is_authenticated"
    IS_STAFF: Final[str] = "is_staff"
    IS_SUPERUSER: Final[str] = "is_superuser"

    # Timestamp fields
    LAST_LOGIN: Final[str] = "last_login"
    LAST_LOGIN_AT: Final[str] = "last_login_at"
    LOGIN_COUNT: Final[str] = "login_count"

    # Session fields
    SESSION_ID: Final[str] = "session_id"
    SESSION_TOKEN: Final[str] = "session_token"

    @classmethod
    def get_credential_fields(cls) -> list[str]:
        """
        Get list of user credential field names.

        Returns:
            List of credential-related field names.
        """
        return [cls.USERNAME, cls.EMAIL, cls.PASSWORD, cls.PHONE]

    @classmethod
    def get_token_fields(cls) -> list[str]:
        """
        Get list of authentication token field names.

        Returns:
            List of token-related field names.
        """
        return [cls.TOKEN, cls.REFRESH_TOKEN, cls.ACCESS_TOKEN, cls.RESET_TOKEN]

    @classmethod
    def get_status_fields(cls) -> list[str]:
        """
        Get list of user status field names.

        Returns:
            List of status-related field names.
        """
        return [cls.IS_ACTIVE, cls.IS_VERIFIED, cls.IS_AUTHENTICATED, cls.IS_STAFF]


# Legacy compatibility aliases (deprecated, will be removed in v2.0)
EMAIL = AuthFields.EMAIL
PASSWORD = AuthFields.PASSWORD
USERNAME = AuthFields.USERNAME
