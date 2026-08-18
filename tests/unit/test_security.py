from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_guest_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_meets_policy,
    verify_password,
)
from app.utils.datetime import now_kst


def test_password_policy_requires_upper_digit_special_and_length() -> None:
    assert password_meets_policy("Abcd1234!")  # upper + digit + special + len>=8
    assert password_meets_policy("NOLOWERCASE1!")  # policy has no lowercase requirement
    assert not password_meets_policy("weak")  # too short, no upper/digit/special
    assert not password_meets_policy("alllowercase1!")  # no uppercase
    assert not password_meets_policy("NoDigitsHere!")  # no digit
    assert not password_meets_policy("NoSpecial123")  # no special char
    assert not password_meets_policy("Ab1!")  # too short


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Abcd1234!")
    assert hashed != "Abcd1234!"
    assert verify_password("Abcd1234!", hashed)
    assert not verify_password("WrongPass1!", hashed)


def test_access_token_roundtrip() -> None:
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    payload = decode_token(token)
    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["type"] == "access"


def test_guest_token_expires_at_given_time() -> None:
    expires_at = now_kst() + timedelta(hours=1)
    token = create_guest_token("00000000-0000-0000-0000-000000000002", expires_at)
    payload = decode_token(token)
    assert payload["type"] == "guest"
    assert payload["exp"] == int(expires_at.timestamp())


def test_decode_token_rejects_tampered_token() -> None:
    token = create_access_token("00000000-0000-0000-0000-000000000003")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tampered")


def test_refresh_token_is_hashed_not_stored_raw() -> None:
    raw = generate_refresh_token()
    hashed = hash_refresh_token(raw)
    assert hashed != raw
    assert hash_refresh_token(raw) == hashed  # deterministic
