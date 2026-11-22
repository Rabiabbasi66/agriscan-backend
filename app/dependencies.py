from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId
import logging

from app.database import db
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

# auto_error=False so a missing Authorization header reaches our handler and
# returns a proper 401 + WWW-Authenticate instead of HTTPBearer's default 403.
security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_db() -> AsyncIOMotorDatabase:
    # May be None while MongoDB is unreachable. Handlers that need it check
    # availability themselves (or depend on an auth helper that does), so
    # request-body validation still runs first and returns 422 as usual.
    return db.database


async def _find_active_user(payload: dict) -> dict | None:
    """Look up the active user referenced by a decoded token payload."""
    if db.database is None or "sub" not in payload:
        return None
    try:
        return await db.database.users.find_one(
            {"_id": ObjectId(payload["sub"]), "is_active": True}
        )
    except (InvalidId, TypeError):
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    # Tokens are never logged; only the pass/fail reason is recorded.
    if credentials is None:
        logger.info("Auth rejected: missing bearer token")
        raise _unauthorized("Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        logger.info("Auth rejected: invalid or expired token")
        raise _unauthorized("Invalid or expired token")

    if db.database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    user = await _find_active_user(payload)
    if not user:
        logger.info("Auth rejected: user not found or inactive")
        raise _unauthorized("User not found")

    return user


async def get_current_active_user(
    current_user=Depends(get_current_user),
):
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=403,
            detail="Inactive user",
        )

    return current_user

async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
):
    """Like get_current_user, but returns None instead of raising when no
    valid credentials are supplied.

    Used by POST /predict so existing anonymous scans keep working, while
    authenticated requests get their predictions attributed to the JWT
    subject (user_id) for the Prediction History feature.
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    return await _find_active_user(payload)
