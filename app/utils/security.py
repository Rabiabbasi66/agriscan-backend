from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__rounds=12,
    deprecated="auto",
)

# Decode is pinned to HS256 regardless of the configured algorithm name so a
# token can never talk the verifier into accepting e.g. alg=none or RS256.
_DECODE_ALGORITHMS = ["HS256"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_token(data: dict, expire_delta: timedelta):
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["iat"] = now
    payload["exp"] = now + expire_delta

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(subject: str, extra: dict | None = None):

    data: dict[str, Any] = {
        "sub": subject,
        "type": "access",
    }

    if extra:
        data.update(extra)

    return _create_token(
        data,
        timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str):
    return _create_token(
        {
            "sub": subject,
            "type": "refresh",
        },
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def _decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=_DECODE_ALGORITHMS,
            options={"require": ["exp", "sub"]},
        )
    except PyJWTError:
        return None

    # A token without a usable subject is never valid.
    if not payload.get("sub"):
        return None

    return payload


def decode_access_token(token: str):
    payload = _decode_token(token)
    if payload is None:
        return None

    # Callers only ever see a payload of the expected token type.
    if payload.get("type") != "access":
        return None

    return payload


def decode_refresh_token(token: str):
    payload = _decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "refresh":
        return None

    return payload
