"""Security helpers: password hashing (bcrypt) and JWT / refresh tokens.

- Access token: stateless JWT, 2h (config-driven), type="access".
- Guest token: stateless JWT, expires at the guest session's expiry, type="guest".
- Refresh token: opaque random string, 14d. Only its SHA-256 hash is stored;
  rotation/logout are handled in the auth service against RefreshToken rows.

This module raises only JWT-native errors on decode; the auth dependency maps
them to domain exceptions (UNAUTHORIZED / TOKEN_EXPIRED).
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.utils.datetime import now_kst

ALGORITHM = "HS256"

TokenType = Literal["access", "guest"]


# --- Password (bcrypt) -------------------------------------------------------
def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --- JWT (access / guest) ----------------------------------------------------
def _encode(subject: str, token_type: TokenType, expires_at: datetime) -> str:
    now = now_kst()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    expires_at = now_kst() + timedelta(minutes=settings.access_token_expire_minutes)
    return _encode(user_id, "access", expires_at)


def create_guest_token(guest_session_id: str, expires_at: datetime) -> str:
    return _encode(guest_session_id, "guest", expires_at)


def decode_token(token: str) -> dict[str, Any]:
    """Decode/verify a JWT. Raises jwt.ExpiredSignatureError / jwt.PyJWTError."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])


# --- Refresh token (opaque + hashed) ----------------------------------------
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return now_kst() + timedelta(days=settings.refresh_token_expire_days)
