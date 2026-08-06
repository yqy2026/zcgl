"""Normalization, protection, and display policy for Party identifiers."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Protocol

from ...core.encryption import EncryptionKeyManager, FieldEncryptor

_IDENTIFIER_TYPES = {
    "legal_entity": {
        "unified_social_credit_code",
        "legal_registration_number",
        "foreign_registration_number",
    },
    "individual": {"national_id", "passport"},
}


class _DeterministicEncryptor(Protocol):
    def encrypt_deterministic(self, plaintext: str | None) -> str | None: ...

    def decrypt_deterministic(self, ciphertext: str | None) -> str | None: ...


@dataclass(frozen=True)
class PreparedPartyIdentifier:
    """Storage values derived from one normalized formal identifier."""

    identifier_type: str | None
    value: str | None
    fingerprint: str | None


class PartyIdentifierService:
    """Apply Party-type rules without exposing natural-person plaintext."""

    def __init__(
        self,
        *,
        encryptor: _DeterministicEncryptor | None = None,
        fingerprint_key: bytes | None = None,
    ) -> None:
        if encryptor is None and fingerprint_key is None:
            key_manager = EncryptionKeyManager()
            key = key_manager.get_key()
            self._encryptor = FieldEncryptor(key_manager) if key is not None else None
            self._fingerprint_key = key
        else:
            self._encryptor = encryptor
            self._fingerprint_key = fingerprint_key

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[\s-]+", "", value).upper()

    def prepare(
        self,
        *,
        party_type: str,
        identifier_type: str | None,
        identifier_value: str | None,
    ) -> PreparedPartyIdentifier:
        normalized_type = identifier_type.strip() if identifier_type is not None else ""
        normalized_value = (
            self._normalize(identifier_value) if identifier_value is not None else ""
        )
        if (normalized_type == "") != (normalized_value == ""):
            raise ValueError(
                "identifier_type and identifier_value must be provided together"
            )
        if normalized_type == "":
            return PreparedPartyIdentifier(None, None, None)

        allowed_types = _IDENTIFIER_TYPES.get(party_type, set())
        if normalized_type not in allowed_types:
            raise ValueError(
                f"identifier type {normalized_type!r} is not valid for party type {party_type!r}"
            )

        if party_type == "legal_entity":
            return PreparedPartyIdentifier(normalized_type, normalized_value, None)

        if self._encryptor is None or self._fingerprint_key is None:
            raise RuntimeError("natural-person identifiers require an encryption key")
        encrypted = self._encryptor.encrypt_deterministic(normalized_value)
        if encrypted is None or encrypted == normalized_value:
            raise RuntimeError("natural-person identifier encryption failed")
        fingerprint = hmac.new(
            self._fingerprint_key,
            f"{normalized_type}\0{normalized_value}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return PreparedPartyIdentifier(normalized_type, encrypted, fingerprint)

    def mask(self, *, identifier_type: str, stored_value: str) -> str:
        if identifier_type not in _IDENTIFIER_TYPES["individual"]:
            return stored_value
        if self._encryptor is None:
            raise RuntimeError("natural-person identifiers require an encryption key")
        plaintext = self._encryptor.decrypt_deterministic(stored_value)
        if plaintext is None or plaintext == stored_value:
            raise RuntimeError("natural-person identifier decryption failed")
        if identifier_type == "national_id" and len(plaintext) >= 10:
            return f"{plaintext[:6]}{'*' * (len(plaintext) - 10)}{plaintext[-4:]}"
        if len(plaintext) <= 4:
            return "*" * len(plaintext)
        return f"{plaintext[:2]}{'*' * (len(plaintext) - 6)}{plaintext[-4:]}"


__all__ = ["PartyIdentifierService", "PreparedPartyIdentifier"]
