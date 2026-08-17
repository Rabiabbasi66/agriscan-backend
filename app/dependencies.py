from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import db
from app.utils.security import decode_access_token

# Argon use karo - HTTPBearer (Simple aur best!)
security = HTTPBearer()


def get_db() -> AsyncIOMotorDatabase:
    return db.database


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    print("AUTH HEADER:", credentials)

    token = credentials.credentials
    print("TOKEN:", token)

    payload = decode_access_token(token)
    print("PAYLOAD:", payload)

    if not payload:
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

    print("USER:", user)

    if not user:
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