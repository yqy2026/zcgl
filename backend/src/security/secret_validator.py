"""
Secret validation module for application startup security.

Validates SECRET_KEY and DATA_ENCRYPTION_KEY for strength to prevent
security vulnerabilities from weak or default values.
"""

import os
import re

from src.core.environment import get_environment


class SecretValidationError(Exception):
    """Raised when secret validation fails"""

    def __init__(self, message: str, suggestion: str = ""):
        self.message = message
        self.suggestion = suggestion
        super().__init__(self.message)


class SecretValidator:
    """Validate application secrets for strength"""

    # Common weak patterns to reject
    WEAK_PATTERNS = [
        r"secret",  # Contains "secret"
        r"changeme",  # Contains "changeme"
        r"password",  # Contains "password"
        r"123456",  # Common number sequence
        r"admin",  # Contains "admin"
    ]

    # Example values that indicate unconfigured secrets
    EXAMPLE_VALUES = [
        "your-secret-key-here",
        "change-in-production",
        "replace-with-real-secret",
        "example-secret",
    ]

    def __init__(self) -> None:
        self.env = get_environment()

    def validate(self, secret: str) -> bool:
        """Validate secret strength"""
        errors = []

        # Check length (minimum 32 characters)
        if len(secret) < 32:
            errors.append(f"Secret too short: {len(secret)} characters (minimum 32)")

        # Check for weak patterns
        secret_lower = secret.lower()
        for pattern in self.WEAK_PATTERNS:
            if re.search(pattern, secret_lower):
                errors.append(f"Secret contains weak pattern: '{pattern}'")

        # Check for example values
        if any(example in secret_lower for example in self.EXAMPLE_VALUES):
            errors.append("Secret appears to be an example value")

        # Check character variety
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret)

        if not (has_upper and has_lower and has_digit and has_special):
            errors.append(
                "Secret lacks character variety (requires uppercase, lowercase, digits, and special characters)"
            )

        if errors:
            suggestion = self._generate_suggestion()
            raise SecretValidationError("\n".join(f"- {e}" for e in errors), suggestion)

        return True

    def validate_env_secrets(self) -> bool:
        """Validate all secrets from environment"""
        secrets_to_check = {
            "SECRET_KEY": os.getenv("SECRET_KEY", ""),
            "DATA_ENCRYPTION_KEY": os.getenv("DATA_ENCRYPTION_KEY", ""),
        }

        all_valid = True
        for secret_name, secret_value in secrets_to_check.items():
            if not secret_value:
                print(f"❌ {secret_name} is not set!")
                all_valid = False
            else:
                try:
                    self.validate(secret_value)
                    print(f"✅ {secret_name} is strong")
                except SecretValidationError as e:
                    print(f"❌ {secret_name} validation failed:")
                    print(f"   {e.message}")
                    if e.suggestion:
                        print(f"\n{e.suggestion}")
                    all_valid = False

        return all_valid

    def _generate_suggestion(self) -> str:
        """Generate a strong secret suggestion"""
        import secrets

        suggested = secrets.token_urlsafe(32)
        return f"Suggested strong secret: {suggested}"


# Singleton instance
secret_validator = SecretValidator()
