"""
Role normalization utility for case-insensitive role comparison.

This module provides centralized role handling to fix Issue #2 where the code
checks for "ADMIN" (uppercase) but the actual role value is "admin" (lowercase).

All role comparisons should use RoleNormalizer for case-insensitive matching.
"""

from enum import Enum


# Centralized role definition (matches UserRole but with utility methods)
class Role(str, Enum):
    """Standardized role enum with case-insensitive comparison"""

    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"  # For future use

    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """
        Create Role from string (case-insensitive).

        Args:
            role_str: Role string (e.g., "admin", "ADMIN", "Admin")

        Returns:
            Role enum value

        Raises:
            ValueError: If role string is invalid

        Examples:
            >>> Role.from_string("admin")
            <Role.ADMIN: 'admin'>
            >>> Role.from_string("ADMIN")
            <Role.ADMIN: 'admin'>
        """
        normalized = role_str.lower().strip()
        role_map = {
            "admin": cls.ADMIN,
            "user": cls.USER,
            "moderator": cls.MODERATOR,
        }
        if normalized not in role_map:
            raise ValueError(f"Invalid role: {role_str}")
        return role_map[normalized]


class RoleNormalizer:
    """Utility class for role normalization and comparison"""

    @staticmethod
    def normalize(role: str) -> str:
        """
        Normalize role string to lowercase.

        Args:
            role: Role string in any case

        Returns:
            Normalized lowercase role string

        Examples:
            >>> RoleNormalizer.normalize("ADMIN")
            'admin'
            >>> RoleNormalizer.normalize("  Admin  ")
            'admin'
        """
        return role.lower().strip()

    @staticmethod
    def is_admin(role: str) -> bool:
        """
        Check if role is admin (case-insensitive).

        Args:
            role: Role string to check

        Returns:
            True if role is admin, False otherwise

        Examples:
            >>> RoleNormalizer.is_admin("admin")
            True
            >>> RoleNormalizer.is_admin("ADMIN")
            True
            >>> RoleNormalizer.is_admin("user")
            False
        """
        return RoleNormalizer.normalize(role) == Role.ADMIN.value

    @staticmethod
    def is_user(role: str) -> bool:
        """
        Check if role is user (case-insensitive).

        Args:
            role: Role string to check

        Returns:
            True if role is user, False otherwise

        Examples:
            >>> RoleNormalizer.is_user("user")
            True
            >>> RoleNormalizer.is_user("USER")
            True
            >>> RoleNormalizer.is_user("admin")
            False
        """
        return RoleNormalizer.normalize(role) == Role.USER.value

    @staticmethod
    def validate(role: str) -> Role:
        """
        Validate and return Role enum.

        Args:
            role: Role string to validate

        Returns:
            Role enum value

        Raises:
            ValueError: If role is invalid

        Examples:
            >>> RoleNormalizer.validate("admin")
            <Role.ADMIN: 'admin'>
        """
        return Role.from_string(role)

    @staticmethod
    def equals(role1: str, role2: str) -> bool:
        """
        Compare two roles (case-insensitive).

        Args:
            role1: First role string
            role2: Second role string

        Returns:
            True if roles are equal (case-insensitive), False otherwise

        Examples:
            >>> RoleNormalizer.equals("admin", "ADMIN")
            True
            >>> RoleNormalizer.equals("admin", "user")
            False
        """
        return RoleNormalizer.normalize(role1) == RoleNormalizer.normalize(role2)
