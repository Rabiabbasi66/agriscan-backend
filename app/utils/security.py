from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_token(data: dict, expire_delta: timedelta):
    payload = data.copy()
    payload["iat"] = datetime.now(timezone.utc)
    payload["exp"] = datetime.now(timezone.utc) + expire_delta

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


def decode_access_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        print("DECODED PAYLOAD:", payload)

        if payload.get("type") != "access":
            print("TOKEN TYPE ERROR:", payload.get("type"))
            return None

        return payload

    except JWTError as e:
        print("JWT DECODE ERROR:", e)
        return None


def decode_refresh_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != "refresh":
            return None

        return payload

    except JWTError:
        return None