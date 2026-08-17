from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.user import UserRegister, UserLogin, TokenResponse
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def register_user(data: UserRegister, db: AsyncIOMotorDatabase) -> dict:
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.phone and await db.users.find_one({"phone": data.phone}):
        raise HTTPException(status_code=400, detail="Phone number already in use")

    now = datetime.now(timezone.utc)
    user_doc = {
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "full_name": data.full_name,
        "phone": data.phone,
        "role": data.role,
        "is_active": True,
        "profile_pic": None,
        "fcm_token": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    logger.info("New user registered: %s (role=%s)", data.email, data.role)
    return user_doc


async def authenticate_user(data: UserLogin, db: AsyncIOMotorDatabase) -> TokenResponse:
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Account is deactivated")

    user_id = str(user["_id"])
    access_token = create_access_token(user_id, extra={"role": user["role"]})
    refresh_token = create_refresh_token(user_id)

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    logger.info("User logged in: %s", data.email)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_tokens(refresh_token: str, db: AsyncIOMotorDatabase) -> TokenResponse:
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    user = await db.users.find_one({"_id": ObjectId(user_id), "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user_id, extra={"role": user["role"]})
    new_refresh = create_refresh_token(user_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
