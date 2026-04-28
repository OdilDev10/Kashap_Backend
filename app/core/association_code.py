"""Helpers for lender-customer association verification codes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
TOKEN_TYPE = "association_link"


def create_association_code(lender_id: str, expires_minutes: int = 30) -> str:
    """Create a short-lived signed code that represents a lender."""
    now = datetime.now(UTC)
    payload = {
        "typ": TOKEN_TYPE,
        "lid": lender_id,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_association_code(code: str) -> str:
    """Validate code signature/expiry and return lender_id."""
    payload = jwt.decode(code, settings.secret_key, algorithms=[ALGORITHM])
    token_type = payload.get("typ")
    lender_id = payload.get("lid")

    if token_type != TOKEN_TYPE or not isinstance(lender_id, str) or not lender_id:
        raise JWTError("Invalid association code payload")

    return lender_id
