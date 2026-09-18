from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from app.database import db
from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

# Argon use karo - HTTPBearer (Simple aur best!)
security = HTTPBearer()


def get_db() -> AsyncIOMotorDatabase:
    return db.database


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    # Phase 12: credentials/tokens are never logged (the previous debug
    # prints leaked the raw bearer token to stdout). Only non-sensitive
    # pass/fail information is logged.
    token = credentials.credentials

    payload = decode_access_token(token)
    if not payload:
        logger.info("Auth rejected: invalid or expired token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = await db.database.users.find_one(
        {
            "_id": ObjectId(payload["sub"]),
            "is_active": True,
        }
    )

    if not user:
        logger.info("Auth rejected: user not found or inactive")
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

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
    if not payload or "sub" not in payload:
        return None

    try:
        user = await db.database.users.find_one(
            {
                "_id": ObjectId(payload["sub"]),
                "is_active": True,
            }
        )
    except Exception:
        return None

    return user
