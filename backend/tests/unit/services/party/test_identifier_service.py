"""Party formal identifier policy tests."""

from __future__ import annotations

import pytest

from src.services.party.identifier_service import PartyIdentifierService


class _Encryptor:
    def encrypt_deterministic(self, value: str) -> str:
        return f"enc:v1:det:{value[::-1]}"

    def decrypt_deterministic(self, value: str) -> str:
        return value.removeprefix("enc:v1:det:")[::-1]


def test_legal_identifier_is_normalized_without_fingerprint() -> None:
    service = PartyIdentifierService(encryptor=None, fingerprint_key=None)

    prepared = service.prepare(
        party_type="legal_entity",
        identifier_type="unified_social_credit_code",
        identifier_value=" 91440101231229726p ",
    )

    assert prepared.value == "91440101231229726P"
    assert prepared.fingerprint is None


def test_natural_identifier_is_encrypted_and_fingerprinted_deterministically() -> None:
    service = PartyIdentifierService(
        encryptor=_Encryptor(),
        fingerprint_key=b"test-fingerprint-key",
    )

    first = service.prepare(
        party_type="individual",
        identifier_type="national_id",
        identifier_value="440101 19900101 123x",
    )
    second = service.prepare(
        party_type="individual",
        identifier_type="national_id",
        identifier_value="44010119900101123X",
    )

    assert first.value.startswith("enc:v1:det:")
    assert first.value != "44010119900101123X"
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint or "") == 64
    assert (
        service.mask(
            identifier_type="national_id",
            stored_value=first.value,
        )
        == "440101********123X"
    )


def test_identifier_pair_and_party_type_mismatch_fail_loud() -> None:
    service = PartyIdentifierService(encryptor=None, fingerprint_key=None)

    with pytest.raises(ValueError, match="provided together"):
        service.prepare(
            party_type="legal_entity",
            identifier_type="unified_social_credit_code",
            identifier_value=None,
        )

    with pytest.raises(ValueError, match="not valid for party type"):
        service.prepare(
            party_type="legal_entity",
            identifier_type="national_id",
            identifier_value="44010119900101123X",
        )


def test_natural_identifier_rejects_missing_encryption_key() -> None:
    service = PartyIdentifierService(encryptor=None, fingerprint_key=b"")

    with pytest.raises(RuntimeError, match="encryption key"):
        service.prepare(
            party_type="individual",
            identifier_type="passport",
            identifier_value="E12345678",
        )
